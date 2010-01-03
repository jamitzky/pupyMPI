__version__ = 0.2 # It bumps the version or else it gets the hose again!

import sys
from optparse import OptionParser, OptionGroup
import threading, sys, getopt, time
from threading import Thread
        
from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.network import Network
from mpi.group import Group 
from mpi.exceptions import MPIException
from mpi import constants 
from mpi.network.utils import pickle

from mpi.request import Request

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

        options, args = parser.parse_args()


        if options.process_io == "remotefile": 
            # Initialise the logger - hackish
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, True)
            filename = constants.LOGDIR+'mpi.local.rank%s.log' % options.rank
            logger.debug("Opening file for I/O: %s" % filename)
            output = open(filename, "w")
            sys.stdout = output
            sys.stderr = output
        elif options.process_io == "none":
            # Initialise the logger - hackish
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, True)
            logger.debug("Closing stdout")
            sys.stdout = None
        else:
            # Initialise the logger
            logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)

        logger.debug("Starting with options: %s %s" % (options.disable_full_network_startup, options.socket_pool_size))
            

        # First check for required Python version
        self._version_check()

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
        # listen on the correcsponding network channels
        self.network.MPI_COMM_WORLD = self.MPI_COMM_WORLD
        
        # Change the contents of sys.argv runtime, so the user processes 
        # can't see all the mpi specific junk parameters we start with.
        user_options =[sys.argv[0], ] 
        user_options.extend(sys.argv[sys.argv.index("--")+1:])
        sys.argv = user_options

        # Set a static attribute on the class so we know it is initialised.
        self.__class__._initialized = True
        
        # Set up the global mpi constants
        constants.MPI_GROUP_EMPTY = Group()
        
        # Data structures for jobs.
        # The locks are for guarding the data structures
        # The events are for signalling change in data structures
        
        # Unstarted requests are both send and receive requests, held here so the user thread can return quickly
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
        
        self.daemon = True
        self.start()

        # Makes every node connect to each other if the settings allow us to do that.
        self.network.start_full_network()
        #logger.info("MPI environment is up and running.")

    def match_pending(self, request):
        """
        Tries to match a pending request with something in
        the received data.
        
        If the received data is found we remove it from the
        list.
        
        The request is updated with the data if found and this
        status update returned from the function so it's possible
        to remove the item from the list.
        
        FIXME: This function is called for all requests in the pending_requests list
        so ideally we should find the data more effectively than linear search
        OTOH: We like the fact that ordering is preserved via current methods
        """
        match = False
        remove = [] 
        with self.received_data_lock:
            for data in self.received_data:
                (communicator_id, sender, tag, acknowledge, message) = data
                
                # Any communication must take place within the same communicator
                if request.communicator.id == communicator_id:
                    
                    # The participant must match or any rank have been specified
                    if request.participant in (sender, constants.MPI_SOURCE_ANY):
                        
                        # The tag must match or any tag have been specified or it must be an acknowledgement (system message)
                        if (request.tag == tag) or (request.tag in (constants.MPI_TAG_ANY, constants.TAG_ACK) and tag > 0):
                            remove.append(data)                            
                            request.update(status="ready", data=message)
                            match = True
                            # Outgoing synchronized communication requires acknowledgement
                            if acknowledge:
                                Logger().debug("SSEND RECIEVED request: %s" % request)
                                # Generate an acknowledge message as an isend
                                # TODO: Consider using an empty message string, to save resources
                                self.communicators[communicator_id].isend(sender, "ACKNOWLEDGEMENT", constants.TAG_ACK)
                            # System message: Acknowledge receive of ssend
                            elif request.tag == constants.TAG_ACK:
                                # FIXME: We should also change state on outgoing request here?
                                Logger().debug("ACK RECIEVED request: %s" % request)
                            
                            break # We can only find matching data for one request and we have
                        
            for data in remove:
                self.received_data.remove(data)
        return match

    def run(self):
        #DEBUG / PROFILING
        #yappi.start(True) # True means also profile built-in functions

        while not self.shutdown_event.is_set():            
            # NOTE: If someone sets this event between the wait and the clear that
            # signal will be missed, but that is just fine since we are about to
            # check the queues anyway
            self.has_work_event.wait()
            self.has_work_event.clear()
            
            # Schedule unstarted requests (may be in- or outbound)
            if self.unstarted_requests_has_work.is_set():
                with self.unstarted_requests_lock:
                    for request in self.unstarted_requests:
                        self.network.t_out.add_out_request(request)

                    self.unstarted_requests = []
                    self.unstarted_requests_has_work.clear()
                
            # Unpickle raw data (received messages) and put them in received queue
            if self.raw_data_has_work.is_set():
                with self.raw_data_lock:
                    with self.received_data_lock:
                        for raw_data in self.raw_data_queue:
                            data = pickle.loads(raw_data)
                            self.received_data.append(data)
                        
                        self.pending_requests_has_work.set()
                        self.raw_data_queue = []
                    self.raw_data_has_work.clear()
                    
            # Pending requests are receive requests the may have a matching recv posted (actual message recieved)
            if self.pending_requests_has_work.is_set():
                with self.pending_requests_lock:
                    removal = [] # Remember succesfully matched requests so we can remove them
                    for request in self.pending_requests:
                        if self.match_pending(request):
                            # FIXME: Either here or in the match_pending we need to
                            # issue a send with a reciept
                            
                            # The matcher function does the actual request update
                            # and will remove matched data from received_data queue
                            # we only need to update our own queue
                            removal.append(request)
                    
                    for request in removal:
                        self.pending_requests.remove(request)

                    self.pending_requests_has_work.clear() # We can't match for now wait until further data received

        # The main loop is now done. We flush all the messages so there are not any outbound messages
        # stuck in the pipline.
        # NOTE: I don't think this flushing can work for acks if the network thread doesn't get a slice
        
        Logger().debug("QUITTY: unstarted requests: %s" % self.unstarted_requests)
        Logger().debug("QUITTY: t_out: %s " % (self.network.t_out.socket_to_request ) )

        with self.unstarted_requests_lock:
            for request in self.unstarted_requests:
                self.network.t_out.add_out_request(request)
            self.unstarted_requests = []
            self.unstarted_requests_has_work.clear()
            
        Logger().debug("QUITTING: unstarted requests: %s" % self.unstarted_requests)
        Logger().debug("QUITTING: raw data: %s" % self.raw_data_queue)
        Logger().debug("QUITTING: recieved data: %s" % self.received_data)
        Logger().debug("QUITTING: pending_requests: %s" % self.pending_requests)
        Logger().debug("QUITTING: t_out: %s " % (self.network.t_out.socket_to_request ) )
        Logger().info("MPI environment shutting down.")
        
        self.queues_flushed.set()

        Logger().debug("Queues flushed and user thread has been signalled.")
        if sys.stdout is not None:
            sys.stdout.flush() # Dirty hack to get the rest of the output out
        

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

        world.waitall(request_list)

        # We have tried to signal every process so we can "safely" exit.
        sys.exit(1)

    def handle_system_message(self, rank, command, raw_data):
        if command == constants.CMD_ABORT:
            Logger().info("Got abort command!")

            # FIXME: This might not actually delay all the threads. We
            # need something more conclusive in the test cases. 
            sys.exit(1)

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
        #Logger().debug("--- Setting shutdown event ---")
        
        self.shutdown_event.set() # signal shutdown to mpi thread
        self.has_work_event.set() # let mpi thread once through the run loop in case it is stalled waiting for work        
        
        #Logger().debug("--- Waiting for mpi thread to flush --")
        
        self.queues_flushed.wait()
        
        Logger().debug("--- Queues flushed mpi thread dead, finalizing network thread(s) --")
            
        # We have now flushed all messages to the network layer. So we signal that it's time
        # to close
        self.network.finalize()
        #Logger().debug("--- Network finally finalized --")
        
        # DEBUG / PROFILING
        # yappi.SORTTYPE_TTOTAL: Sorts the results according to their total time.
        # yappi.SORTTYPE_TSUB : Sorts the results according to their total subtime.
        #   Subtime means the total spent time in the function minus the total time spent in the other functions called from this function. 
        #stats = yappi.get_stats(yappi.SORTTYPE_TSUB,yappi.SORTORDER_DESCENDING, 200 )
        #for stat in stats: print stat
        #yappi.stop()


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
                    
    def get_count(self, arg):
        # FIXME
        pass
        
    def get_elements(self, arg):
        # FIXME
        pass
    def get_processor_name(self, arg):
        # FIXME
        pass
        
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
    
    def _increment_request_id():
        """
        Threadsafe incrementing and return of request ids
        """    
        with self.current_request_id_lock:            
            self.current_request_id += 1
            return self.current_request_id
        
        

