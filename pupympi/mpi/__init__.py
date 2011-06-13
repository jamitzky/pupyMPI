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
__version__ = "0.9.2" # It bumps the version or else it gets the hose again!

import sys, hashlib, random, os
from optparse import OptionParser, OptionGroup
import threading, getopt, time
from threading import Thread
import numpy

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.network import Network
from mpi.group import Group
from mpi.exceptions import MPIException
from mpi import constants
from mpi.network.utils import pickle, robust_send, prepare_message
import mpi.network.utils as utils

from mpi.syscommands import handle_system_commands, execute_system_commands
from mpi.request import Request

import time

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

    user_register = None
    """
    A dict created for the users to input values in. The dict can be read from
    the commandline with the :ref:`readregister.py utility <readregister>`. This
    is useful when you don not want a lot of print output, but need to keep
    an eye with the progress / state of a running instance. The the utility
    documentation for an example.
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

        # Startup time. Used in Wtime() implementation.
        self.startup_timestamp = time.time()

        # Event for handling thread packing.
        self.packing = threading.Event()

        # Data structures for jobs.
        # The locks are for guarding the data structures
        # The events are for signalling change in data structures

        # Unstarted requests are send requests, outbound requests are held here so the user thread can return quickly
        # TRW
        #self.unstarted_requests = []
        #self.unstarted_requests_lock = threading.Lock()
        #self.unstarted_requests_has_work = threading.Event()

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

        # Unstarted collective requests.
        self.unstarted_collective_requests = []
        self.unstarted_collective_requests_lock = threading.Lock()
        self.unstarted_collective_requests_has_work = threading.Event()

        # When the collective requsts are started they are moved to this queue until
        # they are finished.
        self.pending_collective_requests = []
        self.pending_collective_requests_lock = threading.Lock()

        self.received_collective_data_lock = threading.Lock()
        self.received_collective_data = []
        self.pending_collective_requests_has_work = threading.Event()

        # The settings module. This will be handle proper by the
        # function ``generate_settings``.
        self.settings = None
        self.config_callbacks = []

        # Append callbacks
        from mpi.settings import standard_callbacks
        self.config_callbacks.extend(standard_callbacks)

        options = self.parse_options()

        # TODO: See if logger initialisations below here shouldn't be refactored into one

        # Decide how to deal with I/O
        if options.process_io == "remotefile":
            # Initialise the logger

            logger = Logger(os.path.join(options.logdir,"remotelog"), "proc-%d" % options.rank, options.debug, options.verbosity, True)
            filename = constants.DEFAULT_LOGDIR+'mpi.local.rank%s.log' % options.rank


            logger.debug("Opening file for I/O: %s" % filename)
            try:
                output = open(filename, "w")
            except:
                raise MPIException("File for I/O not writeable - check that this path exists and is writeable:\n%s" % constants.DEFAULT_LOGDIR)

            sys.stdout = output
            sys.stderr = output
        elif options.process_io == "none":
            # Initialise the logger
            logger = Logger(options.logdir+"mpi", "proc-%d" % options.rank, options.debug, options.verbosity, True)
            logger.debug("Closing stdout")
            sys.stdout = None
        else:
            # Initialise the logger
            logger = Logger(options.logdir+"mpi", "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)

        # TODO: Put this info under settings when they start to work properly
        #       Also we should check that the path here is accessible and valid
        # if filepath starts with something else than / it is a relative path and we assume it relative to pupympi dir
        if not options.logdir.startswith('/'):
            _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.logdir = os.path.join(_BASE,options.logdir)
        else:
            self.logdir = options.logdir

        # Parse and save settings.
        self.generate_settings(options.settings)

        # Attributes for the security component.
        self.disable_utilities = options.disable_utilities
        self.security_component = None

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

        # Set a resume parameter indicating if we are resuming a packed job.
        # This will be changed (maybe) in the netowrk startup.
        self.resume = False

        # Enable a register for the users to put values in. This register can be read
        # with the readregister.py script found in bin/utils/
        self.user_register = {}

        # Place to keep functions needed when packing / unpacking the running MPI
        # instance. The best place to start is migrate.py
        self.migrate_onpack = None

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

        resumer = None
        if self.resume:
            resumer = self.resume_packed_state()

        self.start()

        # Make every node connect to each other if settings specify it
        if not options.disable_full_network_startup:
            self.network.start_full_network()

        self.initinfo = (self.MPI_COMM_WORLD, self.MPI_COMM_WORLD.rank(), self.MPI_COMM_WORLD.size())

        # Set a static attribute on the class so we know it is initialised.
        self.__class__._initialized = True

        if self._profiler_enabled:
            pupyprof.start()

        if self.resume and resumer:
            resumer(self)


    def parse_options(self):
        parser = OptionParser()
        parser.add_option('--rank', type='int')
        parser.add_option('--size', type='int')
        parser.add_option('--verbosity', type='int')
        parser.add_option('--debug', action='store_true')
        parser.add_option('--quiet', action='store_true')
        parser.add_option('--logdir', dest='logdir', default=constants.DEFAULT_LOGDIR)
        parser.add_option('--network-type', dest='network_type')
        parser.add_option('--mpirun-conn-port', dest='mpi_conn_port')
        parser.add_option('--mpirun-conn-host', dest='mpi_conn_host')
        parser.add_option('--single-communication-thread', dest='single_communication_thread')
        parser.add_option('--process-io', dest='process_io')
        parser.add_option('--disable-full-network-startup', dest='disable_full_network_startup', action="store_true")
        parser.add_option('--disable-unixsockets', dest='unixsockets', default=True, action='store_false')
        parser.add_option('--socket-pool-size', type='int', dest='socket_pool_size')
        parser.add_option('--socket-poll-method', dest='socket_poll_method', default=False)
        parser.add_option('--yappi', dest='yappi', action="store_true", default=False)
        parser.add_option('--yappi-sorttype', dest='yappi_sorttype')
        parser.add_option('--enable-profiling', dest='enable_profiling', action='store_true', default=False)
        parser.add_option('--disable-utilities', dest='disable_utilities', action='store_false')
        parser.add_option('--start-type', dest='start_type', default='normal')
        parser.add_option("--settings", dest="settings", default=None)

        # _ is args
        options, _ = parser.parse_args()
        return options

    def generate_settings(self, settings):
        # We first import our normal settings packed with the mpi environment. These
        # will make a good base for all the functionality here. If the user supplies
        # any other settings files these will override the ones in our module.
        from mpi import settings as base_settings
        self.settings = base_settings

        if settings:
            settings = settings.strip().strip(", ")
            modules = settings.split(",")
            for module in modules:
                # help people a bit
                module = module.strip().strip(".py")

                try:
                    mod = __import__(module)
                    self.settings.__dict__.update(mod.__dict__)

                except ImportError:
                    #Logger().debug("Can not import a settings module by the name of %s" % module)
                    pass
                except Exception, e:
                    Logger().error("Something very wrong happened with your settings module:", e)


    def resume_packed_state(self):
        from mpi import dill
        obj = dill.loads(self.resume_state)
        session_data = obj['session']

        # Import everything from the user module. This is important as the user
        # might have defined objects / classes etc deleted as part of the
        # pickle process.
        user_module = obj['mpi']['user_module']

        try:
            user_module = __import__(user_module)
            import __main__

            for k in user_module.__dict__:
                if k not in __main__.__dict__:
                    __main__.__dict__[k] = user_module.__dict__[k]

            user_module.__dict__.update(__main__.__dict__)

        except Exception, e:
            Logger().warning("Can't import the user module: %s. This might not be a problem, but it is better to restore the script with your script in your PYTHONPATH." % user_module)
            print e

        # Restore the mpi state.
        for att_name in obj['mpi']:
            setattr(self, att_name, obj['mpi'][att_name])

        # The MPI state contains a list of request objects. There can not be a
        # lock object, so only the request state if present now. We restore it
        # with a helper function.
        # TRW
        #self.unstarted_requests = [ Request.from_state(state, self) for state in self.unstarted_requests ]
        self.pending_requests = [ Request.from_state(state, self) for state in self.pending_requests ]

        # FIXME: Setup the communicator and groups.

        # Find a user supplied function (if any) and call it so the user script can restore any
        # unsafe objects if needed.
        unpacker_name = self.get_migrate_onunpack().__name__
        unpacker = getattr(user_module, unpacker_name)

        user_module.__dict__.update(session_data.__dict__)

        # Find the function we need to resume
        resumer = getattr(user_module, self.resumer.__name__)
        return resumer

    def set_migrate_onpack(self, callback):
        """
        Use this function to set a callback the MPI instance should call if the
        system is being migrated. This is useful if you use threaded
        programming which can not be packed directly. This method should then
        tear down those structures and create them aagin on the other side with
        the function set by :func:`set_migrate_onunpack`.
        """
        if not callable(callback):
            raise Exception("The supplied parameter is not callable.")

        self.migrate_onpack = callback

    def get_migrate_onpack(self):
        """
        Returns the callable (or None) used when the running instance is
        migrated.
        """
        return self.migrate_onpack

    def set_migrate_onunpack(self, callback):
        """
        Use this function to set a callback the MPI instance should call if the
        system is being migrated. This is useful if you use threaded
        programming which can not be packed directly. This method should then
        setup those structures.
        """
        if not callable(callback):
            raise Exception("The supplied parameter is not callable.")

        self.migrate_onunpack = callback

    def get_migrate_onunpack(self):
        """
        Returns the callable (or None) used when the running instance is
        migrated (setup on the other side).
        """
        return getattr(self, "migrate_onunpack", None)

    def set_resume_function(self, callback):
        """
        Set the function responsible for resuming an instance run. See the
        section about migrating a running instance.
        """
        if not callable(callback):
            raise Exception("The supplied parameter is not callable.")

        self.resume_function = callback

    def match_collective_pending(self):
        """
        Look through all the pending collective requests and match them with
        the received data.
        """
        prune = False
        #DEBUG
        #Logger().debug("match_collective_pending: going in")

        with self.pending_collective_requests_lock:
            with self.received_collective_data_lock:
                new_data_list = []

                for item in self.received_collective_data:
                    (rank, msg_type, tag, ack, comm_id, coll_class_id, raw_data) = item

                    match = False
                    for request in self.pending_collective_requests:
                        if request.communicator.id == comm_id and request.tag == tag:
                            try:
                                match = request.accept_msg(rank, raw_data, msg_type)
                                
                                # Check if we can overtake the request object in stead.
                                
                            except TypeError, e:
                                Logger().error("rank:%i got TypeError:%s when accepting msg for request of type:%s" % (rank, e, request.__class__) )

                            if match:
                                # DEBUG
                                #Logger().debug("match FOUND for - rank:%i, tag:%i" % (rank,tag))
                                if request.test():
                                    prune = True
                                break

                    if not match:
                        new_data_list.append( item )

                self.received_collective_data = new_data_list

            if prune:
                # We remove all the requests marked as completed.
                self.pending_collective_requests = [r for r in self.pending_collective_requests if not r.test()]

    def match_pending(self, request):
        """
        Tries to match a pending request with something in the received data.

        If the received data is found we remove it from the list.

        The request is updated with the data if found and this
        status update returned from the function so it is possible
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
                                Logger().debug("SSEND RECEIVED request: %s" % request)
                                # Generate an acknowledge message as an isend
                                # NOTE: Consider using an empty message string, to save (a little) resources
                                self.communicators[communicator_id]._isend( "ACKNOWLEDGEMENT", sender, constants.TAG_ACK)
                            # System message: Acknowledge receive of ssend
                            elif request.tag == constants.TAG_ACK:
                                Logger().debug("ACK RECEIVED request: %s" % request)

                            break # We can only find matching data for one request and we have

            for data in remove:
                self.received_data.remove(data)
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

            #Logger().debug("--No more wait for work")

            # Unpickle raw data (received messages) and put them in received queue
            if self.raw_data_has_work.is_set():
                with self.raw_data_lock:
                    # FIXME: The received_data_lock does not need to be held here,
                    # instead it should be enough to lock around the append and set() as is the case for received_collective_data_lock
                    with self.received_data_lock:
                        for element in self.raw_data_queue:
                            (rank, msg_type, tag, ack, comm_id, coll_class_id, raw_data) = element

                            if tag in constants.COLLECTIVE_TAGS:
                                # Messages that are part of a collective request, are handled
                                # on a seperate queue and matched and deserialized later
                                with self.received_collective_data_lock:
                                    self.received_collective_data.append(element)
                                    self.pending_collective_requests_has_work.set()

                            else:
                                data = utils.deserialize_message(raw_data, msg_type)
                                self.received_data.append( (rank, tag, ack, comm_id, data) )
                                self.pending_requests_has_work.set()
                        self.raw_data_queue = []
                    self.raw_data_has_work.clear()

            # Collective requests.
            if self.unstarted_collective_requests_has_work.is_set():
                self.unstarted_collective_requests_has_work.clear()
                with self.unstarted_collective_requests_lock:
                    for coll_req in self.unstarted_collective_requests:
                        coll_req.start()

                    with self.pending_collective_requests_lock:
                        self.pending_collective_requests.extend(self.unstarted_collective_requests)
                        self.unstarted_collective_requests = []
                self.pending_collective_requests_has_work.set()

            if self.pending_collective_requests_has_work.is_set():
                # DEBUG
                #Logger().debug("Trying to match collective pending")

                self.match_collective_pending()
                # NOTE: Codus Rex made a boo-boo here since he neglected to clear the signal
                # If the list is empty clear the signal
                if not self.pending_collective_requests:
                    self.pending_collective_requests_has_work.clear()
                else:
                    # NOTE: This solution is too harsh
                    # Signal self that more is to come
                    #self.has_work_event.set()
                    pass

            # Pending requests are receive requests they may have a matching recv posted (actual message recieved)
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


        # TODO: Remove this when TRW is in effect again
        self.queues_flushed.set()

        # Start built-in profiling facility
        if self._profiler_enabled:
            pupyprof.stop()
            pupyprof.dump_stats(os.path.join(self.logdir,'prof.rank%s.log' % self.MPI_COMM_WORLD.rank()))
            Logger().debug("Writing profiling traces to %s" % self.logdir)

        if self._yappi_enabled:
            yappi.stop()

            filename = os.path.join(self.logdir,'yappi.rank%s.log' % self.MPI_COMM_WORLD.rank())
            Logger().debug("Writing yappi stats to %s" % filename)
            try:
                f = open(filename, "w")
            except:
                raise MPIException("Logging directory not writeable - check that this path exists and is writeable:\n%s" % constants.DEFAULT_LOGDIR)

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
        user_module = sys.argv[0].split("/")[-1].replace(".py","")

        return {
            # TRW
            #'unstarted_requests' : [r.get_state() for r in self.unstarted_requests],
            'pending_requests' : [r.get_state() for r in self.pending_requests],
            'raw_data_queue' : self.raw_data_queue,
            'received_data' : self.received_data,
            'current_request_id' : self.current_request_id,
            'pending_systems_commands' : self.pending_systems_commands,
            'migrate_onpack' : getattr(self, "migrate_onpack", None),
            'migrate_onunpack' : getattr(self, "migrate_onunpack", None),
            'resumer' : self.resume_function,
            'user_module' : user_module,
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

            # FIXME: Why is cmd not set on Request initialization?
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

    def set_configuration(self, config_data):
        """
        Change - if possible - the configuration parameters. The function
        will return a dict with the configration setting name as the index
        and a (boo, string) indicating if the parameter was changed.
        """
        res = {}
        for set_name in config_data:
            set_value = config_data[set_name]
            res[set_name] = self._set_config(set_name, set_value)

        return res

    def _set_config(self, name, value):
        """
        An internal function for setting configurations elements. This is not
        only used in the function above can also be used otherwere in the
        system.
        """
        # First check. Check if the setting is defined in our settings
        # module. If not, the settings simply does not exists.
        val = None
        try:
            val = getattr(self.settings, name)
        except AttributeError:
            return (False, "No such setting!")

        # Try to type case
        try:
            value = type(val)(value)
        except ValueError:
            return (False, "Can not cast this setting into the required value. Required value is %s" % type(val))

        # Check if there are any callbacks for this setting
        callbacks = self.config_callbacks
        valid = True
        if callbacks:
            valid = all([c(name) for c in callbacks])

        if not valid:
            return (False, "Access to this configuration is restricted")

        # ALL is okay and we change the setting.
        setattr(self.settings, name, value)

        return (True, "Changed!")

    def handle_system_message(self, rank, command, raw_data, connection):
        """
        Handle a system message. We define a list of read only commands and all
        others are considered writeable. The raw data contains a security
        component we need to check in the case of a write command.

        This method returns a boolean indicating if the command was actually
        tried.
        """
        read_only = (constants.CMD_PING, constants.CMD_READ_REGISTER)
        commands = (constants.CMD_CONFIG, constants.CMD_ABORT, constants.CMD_PING, constants.CMD_MIGRATE_PACK, constants.CMD_READ_REGISTER, constants.CMD_CONN_CLOSE)

        data = pickle.loads(raw_data)
        user_data = None
        security_component = None

        if isinstance(data, tuple):
            security_component, user_data = data
        else:
            security_component = data

        # Security check.
        if command not in read_only:
            if security_component != self.get_security_component() and rank < 0:
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

    def get_version(self):
        """
        Return the version number of the pupyMPI installation.
        """
        execute_system_commands(self.mpi)
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

