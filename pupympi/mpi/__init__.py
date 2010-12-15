#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
#
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
__version__ = 0.8 # It bumps the version or else it gets the hose again!

import sys, hashlib, random
from optparse import OptionParser, OptionGroup
import threading, getopt, time
from threading import Thread

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.network import Network
from mpi.group import Group
from mpi.exceptions import MPIException
from mpi import constants
from mpi.network.utils import pickle, robust_send, prepare_message

from mpi.syscommands import handle_system_commands
from mpi.request import Request

try:
    import yappi
except ImportError:
    pass

try:
    import pupyprof
except ImportError:
    pass

class MPI(Thread):
    """
    This is the main class containing most of the public API. Initializing
    the MPI system is done by creating an instance of this class. Via an
    MPI instance a program can interact with other processes through different
    communicators.

    .. note::
        The MPI instance state is a static class variable, so creating multiple
        instances will always yield 'the same' instance, much like a singleton design
        pattern.
    """

    MPI_COMM_WORLD = None
    """
    The largest and first communicator containing all the started processes as
    members.

    Look at the API documentation for :ref:`communicators <api-communicator-label>`
    for more information about the available methods.
    """

    def __init__(self):
        Thread.__init__(self)

        """
        Initializes the MPI environment. This will give each process a separate
        rank in the MPI_COMM_WORLD communicator along with the total number of
        processes in the communicator. Both attributes can be read just after
        startup::

            from mpi import MPI

            mpi = MPI()
            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()

            print "Proc %d of %d started" % (rank, size)

            mpi.finalize()

        """

        self.name = "MPI" # Thread name

        # Event for handling thread packing.
        self.packing = threading.Event()

        # Data structures for jobs.
        # The locks are for guarding the data structures
        # The events are for signalling change in data structures

        # Unstarted requests are send requests, outbound requests are held here so the user thread can return quickly
        self.unstarted_requests = []
        self.unstarted_requests_lock = threading.Lock()

        self.unstarted_requests_has_work = threading.Event()

        # Pending requests are recieve requests where the data may or may not have arrived
        self.pending_requests = []
        self.pending_requests_lock = threading.Lock()
        self.pending_requests_has_work = threading.Event()

        # Raw data are messages that have arrived but not been unpickled yet
        self.raw_data_queue = []
        self.raw_data_lock = threading.Lock()
        self.raw_data_has_work = threading.Event()

        # Recieved data are messages that have arrived and are unpickled
        # (ie. ready for matching with a posted recv request)
        #There are no events as this is handled through the "pending_request_" event.
        self.received_data = []
        self.received_data_lock = threading.Lock()

        # General event to wake up main mpi thread
        self.has_work_event = threading.Event()

        # Shutdown signals
        self.shutdown_event = threading.Event() # MPI finalize has been called, shutdown in progress
        self.queues_flushed = threading.Event() # Queues are flushed, shutting down network threads can begin

        # Lock and counter for enumerating request ids
        self.current_request_id_lock = threading.Lock()
        self.current_request_id = 0

        # Pending system commands. These will be executed at first chance we have (we
        # need access to the user code). We also have a lock around the list, to ensure
        # proper access.
        self.pending_systems_commands = []
        self.pending_systems_commands_lock = threading.Lock()

        parser = OptionParser()
        parser.add_option('--rank', type='int')
        parser.add_option('--size', type='int')
        parser.add_option('--verbosity', type='int')
        parser.add_option('--debug', action='store_true')
        parser.add_option('--quiet', action='store_true')
        parser.add_option('--log-file', dest='logfile', default="mpi")
        parser.add_option('--network-type', dest='network_type')
        parser.add_option('--mpirun-conn-port', dest='mpi_conn_port')
        parser.add_option('--mpirun-conn-host', dest='mpi_conn_host')
        parser.add_option('--single-communication-thread', dest='single_communication_thread')
        parser.add_option('--process-io', dest='process_io')
        parser.add_option('--disable-full-network-startup', dest='disable_full_network_startup', action="store_true")
        parser.add_option('--socket-pool-size', type='int', dest='socket_pool_size')
        parser.add_option('--socket-poll-method', dest='socket_poll_method', default=False)
        parser.add_option('--yappi', dest='yappi', action="store_true", default=False)
        parser.add_option('--yappi-sorttype', dest='yappi_sorttype')
        parser.add_option('--enable-profiling', dest='enable_profiling', action='store_true', default=False)
        parser.add_option('--disable-utilities', dest='disable_utilities', action='store_false')

        # _ is args
        options, _ = parser.parse_args()

        # Attributes for the security component.
        self.disable_utilities = options.disable_utilities
        self.security_component = None

        if options.process_io == "remotefile":
            # Initialise the logger
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, True)
            filename = constants.LOGDIR+'mpi.local.rank%s.log' % options.rank
            logger.debug("Opening file for I/O: %s" % filename)
            try:
                output = open(filename, "w")
            except:
                raise MPIException("File for I/O not writeable - check that this path exists and is writeable:\n%s" % constants.LOGDIR)

            sys.stdout = output
            sys.stderr = output
        elif options.process_io == "none":
            # Initialise the logger
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, True)
            logger.debug("Closing stdout")
            sys.stdout = None
        else:
            # Initialise the logger
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)

        # First check for required Python version
        self._version_check()

        # Check for yappi support
        self._yappi_enabled = False
        if options.yappi:
            try:
                import yappi
                self._yappi_enabled = True
                self._yappi_sorttype = yappi.SORTTYPE_NCALL

                if options.yappi_sorttype:
                    if options.yappi_sorttype == 'name':
                        self._yappi_sorttype = yappi.SORTTYPE_NAME
                    elif options.yappi_sorttype == 'ncall':
                        self._yappi_sorttype = yappi.SORTTYPE_NCALL
                    elif options.yappi_sorttype == 'ttotal':
                        self._yappi_sorttype = yappi.SORTTYPE_TTOTAL
                    elif options.yappi_sorttype == 'tsub':
                        self._yappi_sorttype = yappi.SORTTYPE_TSUB
                    elif options.yappi_sorttype == 'tavg':
                        self._yappi_sorttype = yappi.SORTTYPE_TAVG
                    else:
                        logger.warn("Unknown yappi sorttype '%s' - defaulting to ncall." % options.yappi_sorttype)

            except ImportError:
                logger.warn("Yappi is not supported on this system. Statistics will not be logged.")
                self._yappi_enabled = False

        # Start built-in profiling facility
        self._profiler_enabled = False
        if options.enable_profiling:
            if self._yappi_enabled:
                logger.warn("Running yappi and pupyprof simultaneously is unpossible. Pupyprof has been disabled.");
            else:
                try:
                    import pupyprof
                    self._profiler_enabled = True
                except ImportError:
                    logger.warn("Pupyprof is not supported on this system. Tracefile will not be generated");
                    self._profiler_enabled = False

        self.network = Network(self, options)

        # Create the initial global Group, and assign the network all_procs as members
        world_Group = Group(options.rank)
        world_Group.members = self.network.all_procs

        # Create the initial communicator MPI_COMM_WORLD. It is initialized with
        # the rank of the process that holds it and size.
        # The members are filled out after the network is initialized.
        self.communicators = {}

        self.MPI_COMM_WORLD = Communicator(self, options.rank, options.size, self.network, world_Group, comm_root=None)

        # Tell the network about the global MPI_COMM_WORLD, and let it start to
        # listen on the corresponding network channels
        self.network.MPI_COMM_WORLD = self.MPI_COMM_WORLD

        # Change the contents of sys.argv runtime, so the user processes
        # can't see all the mpi specific parameters we start with.
        user_options =[sys.argv[0], ]
        user_options.extend(sys.argv[sys.argv.index("--")+1:])
        sys.argv = user_options

        # Set up the global mpi constants
        constants.MPI_GROUP_EMPTY = Group()

        self.daemon = True
        self.start()

        # Make every node connect to each other if settings specify it
        if not options.disable_full_network_startup:
            self.network.start_full_network()
        #logger.info("MPI environment is up and running.")

        # Set a static attribute on the class so we know it is initialised.
        self.__class__._initialized = True

        if self._profiler_enabled:
            pupyprof.start()

    def match_pending(self, request):
        """
        Tries to match a pending request with something in
        the received data.

        If the received data is found we remove it from the
        list.

        The request is updated with the data if found and this
        status update returned from the function so it's possible
        to remove the item from the list.
        """
        match = False
        remove = []
        with self.received_data_lock:
            #Logger().debug("-- Match pending has lock! received_data:%s" % self.received_data)

            for element in self.received_data:
                (sender, tag, acknowledge, communicator_id, message) = element

                # Any communication must take place within the same communicator
                if request.communicator.id == communicator_id:

                    # The participant must match or any rank have been specified
                    if request.participant in (sender, constants.MPI_SOURCE_ANY):

                        # The tag must match or any tag have been specified or it must be an acknowledgement (system message)
                        if (request.tag == tag) or (request.tag in (constants.MPI_TAG_ANY, constants.TAG_ACK) and tag > 0):
                            remove.append(element)
                            request.update(status="ready", data=message)
                            match = True
                            # Outgoing synchronized communication requires acknowledgement
                            if acknowledge:
                                Logger().debug("SSEND RECIEVED request: %s" % request)
                                # Generate an acknowledge message as an isend
                                # NOTE: Consider using an empty message string, to save (a little) resources
                                self.communicators[communicator_id]._isend( "ACKNOWLEDGEMENT", sender, constants.TAG_ACK)
                            # System message: Acknowledge receive of ssend
                            elif request.tag == constants.TAG_ACK:
                                Logger().debug("ACK RECIEVED request: %s" % request)

                            break # We can only find matching data for one request and we have

            for data in remove:
                self.received_data.remove(data)
        #Logger().debug("-- Match pending released lock! Match:%s" % match)
        #Logger().warning("Show some request!: %s" % request)
        return match

    def run(self):

        if self._yappi_enabled:
            yappi.start(builtins=True)

        while not self.shutdown_event.is_set():
            # NOTE: If someone sets this event between the wait and the clear that
            # signal will be missed, but that is just fine since we are about to
            # check the queues anyway
            self.has_work_event.wait()
            self.has_work_event.clear()

            # Schedule unstarted requests (outbound requests)
            if self.unstarted_requests_has_work.is_set():
                with self.unstarted_requests_lock:
                    for request in self.unstarted_requests:
                        #Logger().warning("Show some request!: %s" % request)
                        self.network.t_out.add_out_request(request)

                    self.unstarted_requests = []
                    self.unstarted_requests_has_work.clear()

            # Unpickle raw data (received messages) and put them in received queue
            if self.raw_data_has_work.is_set():
                #Logger().debug("raw_data_has_work is set")
                with self.raw_data_lock:
                    with self.received_data_lock:
                        #Logger().debug("got both locks")
                        for element in self.raw_data_queue:
                            (rank, tag, ack, comm_id, raw_data) = element
                            data = pickle.loads(raw_data)
                            self.received_data.append( (rank, tag, ack, comm_id, data) )
                            #Logger().debug("Adding data: %s" % data)

                        self.pending_requests_has_work.set()
                        self.raw_data_queue = []
                    self.raw_data_has_work.clear()

            # Pending requests are receive requests the may have a matching recv posted (actual message recieved)
            if self.pending_requests_has_work.is_set():
                with self.pending_requests_lock:
                    removal = [] # Remember succesfully matched requests so we can remove them
                    for request in self.pending_requests:
                        if self.match_pending(request):
                            # The matcher function does the actual request update
                            # and will remove matched data from received_data queue
                            # we only need to update our own queue
                            removal.append(request)

                    for request in removal:
                        self.pending_requests.remove(request)

                    self.pending_requests_has_work.clear() # We can't match for now wait until further data received


        # We handle packing a bit different.
        if not self.packing.is_set():
            # The main loop is now done. We flush all the messages so there are not any outbound messages
            # stuck in the pipline.
            with self.unstarted_requests_lock:
                for request in self.unstarted_requests:
                    self.network.t_out.add_out_request(request)
                self.unstarted_requests = []
                self.unstarted_requests_has_work.clear()

            self.queues_flushed.set()

            # Start built-in profiling facility
            if self._profiler_enabled:
                pupyprof.stop()
                pupyprof.dump_stats(constants.LOGDIR+'prof.rank%s.log' % self.MPI_COMM_WORLD.rank())

            if self._yappi_enabled:
                yappi.stop()

                filename = constants.LOGDIR+'yappi.rank%s.log' % self.MPI_COMM_WORLD.rank()
                Logger().debug("Writing yappi stats to %s" % filename)
                try:
                    f = open(filename, "w")
                except:
                    raise MPIException("Logging directory not writeable - check that this path exists and is writeable:\n%s" % constants.LOGDIR)

                stats = yappi.get_stats(self._yappi_sorttype)

                for stat in stats:
                    print >>f, stat
                yappi.clear_stats()

                f.close()

            if sys.stdout is not None:
                sys.stdout.flush() # Slight hack to get the rest of the output out

    def get_state(self):
        """
        A function for getting the current state of the MPI environment.
        """
        return {
            'state_origin' : 'mpi',
            'unstarted_requests' : self.unstarted_requests,
            'pending_requests' : self.pending_requests,
            'raw_data_queue' : self.raw_data_queue,
            'received_data' : self.received_data,
            'current_request_id' : self.current_request_id,
            'pending_systems_commands' : self.pending_systems_commands,
        }

    def abort(self):
        """
        Makes a best attempt to cancel all the tasks in the world
        communicator and makes every process shut down. Don't expect
        anything to behave nicely after this call.

        You should use this method if something bad and irreversible
        happens. The system will have a better chance - but it's not
        guaranteed - of finalizing nicely.
        """
        world = self.MPI_COMM_WORLD
        rank = world.rank()
        size = world.size()

        request_list = []
        for r in range(size):
            if r == rank:
                continue

            # send about message to the process with rank r.
            # Create a send request object
            handle = Request("send", world, r, constants.MPI_TAG_ANY, False)
            handle.cmd = constants.CMD_ABORT

            # Add the request to the MPI layer unstarted requests queue. We
            # signal the condition variable to wake the MPI thread and have
            # it handle the request start.
            world._add_unstarted_request(handle)
            request_list.append(handle)

        world._waitall(request_list)

        # We have tried to signal every process so we can "safely" exit.
        sys.exit(1)

    def handle_system_message(self, rank, command, raw_data, connection):
        """
        Handle a system message. We define a list of read only commands and all
        others are considered writeable. The raw data contains a security
        component we need to check in the case of a write command.

        This method returns a boolean indicating if the command was actually
        tried.
        """
        read_only = (constants.CMD_PING, )
        commands = (constants.CMD_ABORT, constants.CMD_PING, constants.CMD_MIGRATE_PACK, )

        data = pickle.loads(raw_data)
        user_data = None
        security_component = None

        if isinstance(data, tuple):
            security_component, user_data = data
        else:
            security_component = data

        # Security check.
        if command not in read_only:
            if security_component != self.get_security_component():
                Logger().warning("Failed security check in system command. Expected security component was %s but received %s for command %s" % (self.get_security_component(), raw_data, command))
                return False

        # Check we have a system command
        if command in commands:
            with self.pending_systems_commands_lock:
                self.pending_systems_commands.append( (command, connection, user_data))
        else:
            print "Error: Unknown system command"

    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles,
        logfiles and sockets.

        Remember to always end your MPI program with this call. Otherwise proper
        shutdown is not guaranteed.

        .. note::
            Part of the finalizing call is to flush all outgoing requests. You
            don't need to wait() on all your started isends before you call
            finalize.
        """
        #Logger().debug("--- Finalize has been called ---")
        self.shutdown_event.set() # signal shutdown to mpi thread
        self.has_work_event.set() # let mpi thread once through the run loop in case it is stalled waiting for work

        self.queues_flushed.wait()

        # We have now flushed all messages to the network layer. So we signal that it's time
        # to close
        self.network.finalize()

        # Asser experimental
        self.join()

    @classmethod
    def initialized(cls):
        """
        Returns a boolean indicating whether the MPI environment is
        initialized::

            from mpi import MPI

            status = MPI.initialized()  # status will be False
            mpi = MPI()

            status = MPI.initialized()  # status will now be True

        .. note::
            This method is usefull if you're using threads in your
            calculation. You can use the method to ensure the MPI
            enviroment is fully initializing before a tread starts
            actual communication.
        """
        return getattr(cls, '_initialized', False)

    @handle_system_commands
    def get_version(self):
        """
        Return the version number of the pupyMPI installation.
        """
        return __version__

    def _version_check(self):
        """
        Check that the required Python version is installed
        """
        (major,minor,_,_,_) = sys.version_info
        if (major == 2 and minor < 6) or major < 2:
            Logger().error("pupyMPI requires Python 2.6 (you may have to kill processes manually)")
            sys.exit(1)
        elif major >= 2 and minor is not 6:
            Logger().warn("pupyMPI is only certified to run on Python 2.6")

    def generate_security_component(self):
        """
        Generate a rank specific security component. This component is saved on
        the MPI instance so requests by the pupyMPI utilities can be checked.

        Note that this is a very limited security model. As long as we are
        primarly dealing with students we just want to avoid somebody finding
        other peoples processes and aborting them because they want the grid
        time.

        Note that no component will be generated if the user did not want to
        allow run time manipulation of the execution environment.
        """
        if self.security_component:
            raise Exception("Security component already genearted!")

        if self.disable_utilities:
            return None

        h = hashlib.sha1()
        h.update(str(time.time()))
        h.update(str(random.random()))

        self.security_component = h.hexdigest()

        return self.get_security_component()

    def get_security_component(self):
        """ Return the generated component """
        return self.security_component

