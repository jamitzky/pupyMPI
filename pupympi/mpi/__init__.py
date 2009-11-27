__version__ = 0.2 # It bumps the version or else it gets the hose again!

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

    NOTE: The MPI instance state is a static class variable, so creating multiple
    instances will always yield 'the same' instance, much like a singleton design
    pattern. 
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

        # Initialise the logger
        logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)

        logger.debug("Starting with options: %s %s" % (options.disable_full_network_startup, options.socket_pool_size))

        if options.process_io == "remotefile": 
            filename = '/tmp/mpi.local.rank%s.log' % options.rank
            logger.debug("Opening file for I/O: %s" % filename)
            output = open(filename, "w")
            sys.stdout = output
            sys.stderr = output
        elif options.process_io == "none":
            logger.debug("Closing stdout")
            sys.stdout = None

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
        #logger.debug("Set the MPI environment to initialised")
        
        # set up 'constants'
        constants.MPI_GROUP_EMPTY = Group()
        
        # Initialising data structures for starting jobs.
        # The locks are for guarding the data structures
        # The events are for signalling change in data structures
        
        # Unstarted requests are both send and receive requests held here so the user thread can return quickly
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
        self.raw_data_event = threading.Event() #FIXME: Rename to _has_work for consistency
        
        # Recieved data are messages that have arrived and are unpickled
        # (ie. ready for matching with a posted recv request)
        #There are no events as this is handled through the "pending_request_" event.
        self.received_data = []
        self.received_data_lock = threading.Lock()

        # General condition to wake up main mpi thread
        self.has_work_cond = threading.Condition()
        
        # Kill signal
        self.shutdown_event = threading.Event()
        
        # Adding locks and initial information about the request queue
        self.current_request_id_lock = threading.Lock()
        self.current_request_id = 0
        
        self.daemon = True # NOTE: Do we really want this? We could die before the network threads
        self.start()

        # Makes every node connect to each other if the settings allow us to do that.
        self.network.start_full_network()
        logger.info("MPI environment is up and running.")

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
                
                # The first strict rule is that any communication must
                # take part in the same communicator.
                if request.communicator.id == communicator_id:
                    
                    # The participants must also match.That is the sender must
                    # have specified this rank and we're gonna accept a message
                    # from that rank or from any rank
                    if request.participant in (sender, constants.MPI_SOURCE_ANY):
                        
                        # The sender / receiver must agree on the tag, or
                        # we must be ready to receive any tag or
                        # it should be an acknowledgement
                        if request.tag in (tag, constants.MPI_TAG_ANY, constants.TAG_ACK):
                            remove.append(data)                            
                            request.update(status="ready", data=message)
                            match = True
                            # Synchronized communication requires acknowledgement
                            if acknowledge:
                                Logger().debug("SSEND RECIEVED request: %s" % request)
                                # Generate an acknowledge message
                                # TODO: Consider using an empty message string, to save resources
                                self.communicators[communicator_id].isend(sender, "ACKNOWLEDGEMENT", constants.TAG_ACK)
                            # System message: Acknowledge receive of ssend
                            elif request.tag == constants.TAG_ACK:
                                Logger().debug("ACK RECIEVED request: %s" % request)

                            
                            break # We can only find matching data for one request and we have
                        
            for data in remove:
                self.received_data.remove(data)
        return match

    def run(self):
    # NOTE: We should consider whether the 3 part division of labor in this loop is
    # good and the ordering optimal
    
        # create internal functions that will be used below
        def _handle_unstarted():
            # Schedule unstarted requests (may be in- or outbound)
            #                if self.unstarted_requests_has_work.is_set():
            with self.unstarted_requests_lock:
                #Logger().debug(debugarg+"Checking unstarted:%s " % self.unstarted_requests)
                for request in self.unstarted_requests:
                    self.schedule_request(request)
                self.unstarted_requests = []
                self.unstarted_requests_has_work.clear()
    
        while not self.shutdown_event.is_set():
            #Logger().debug("Still going, try getting has work cond")
            with self.has_work_cond:
                self.has_work_cond.wait(0.5) 
                
                Logger().debug("Somebody notified has_work_cond. unstarted_requests_has_work(%s), raw_data_event(%s) & pending_requests_has_work (%s)" % (
                        self.unstarted_requests_has_work.is_set(), self.raw_data_event.is_set(), self.pending_requests_has_work.is_set() ))
                Logger().debug("\tunstarted requests: %s" % self.unstarted_requests)
                Logger().debug("\traw data: %s" % self.raw_data_queue)
                Logger().debug("\trecieved data: %s" % self.received_data)
                Logger().debug("\tpending_requests: %s" % self.pending_requests)

                _handle_unstarted()
            
                # Unpickle raw data (received messages) and put them in received queue
#                if self.raw_data_event.is_set():
                with self.raw_data_lock:
                    #Logger().debug("Checking - got raw_data_lock")
                    with self.received_data_lock:
                        #Logger().debug("Checking received:%s " % self.received_data)
                        for raw_data in self.raw_data_queue:
                            data = pickle.loads(raw_data)
                            self.received_data.append(data)
                        
                        self.pending_requests_has_work.set()
                        self.raw_data_queue = []
                    self.raw_data_event.clear()
                        
                # Pending requests are receive requests the may have a matching recv posted (actual message recieved)
#                if self.pending_requests_has_work.is_set():
                with self.pending_requests_lock:
                    #Logger().debug("Checking pending:%s " % self.pending_requests)
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
                        
                    Logger().error("pending_requests_has_work: %s"% (self.pending_requests_has_work))    
                        
                    try:
                        Logger().debug("Gonna try clearing")
                        self.pending_requests_has_work.clear() # We can't match for now wait until further data received
                    except Exception, e:
                        pass

        # The main loop is now done. We flush all the messages so there are not any outbound messages
        # stuck in the pipline.
        # NOTE: I don't think this flushing can work for acks if the network thread doesn't get a slice
        
        #Logger().debug("GOING FOR FINAL PURGE")
        Logger().debug("QUITTY: unstarted requests: %s" % self.unstarted_requests)
        Logger().debug("QUITTY: t_out: %s " % (self.network.t_out.socket_to_request ) )
        _handle_unstarted()
        Logger().debug("QUITTING: unstarted requests: %s" % self.unstarted_requests)
        Logger().debug("QUITTING: raw data: %s" % self.raw_data_queue)
        Logger().debug("QUITTING: recieved data: %s" % self.received_data)
        Logger().debug("QUITTING: pending_requests: %s" % self.pending_requests)
        Logger().debug("QUITTING: t_out: %s " % (self.network.t_out.socket_to_request ) )
<<<<<<< /home/fred/Diku/ppmpi/code/pupympi/mpi/__init__.py
        Logger().info("MPI environment shutting down.")
=======
        
        # Eksperimental
        self.network.finalize()
        
        # DEBUG
        #time.sleep(1)
        #time.sleep(2)
        
>>>>>>> /tmp/__init__.py~other.k4VE7E
        # DEBUG
        if sys.stdout is not None:
            sys.stdout.flush() # Dirty hack to get the rest of the output out

        
    def schedule_request(self, request):
        #Logger().debug("Schedule request for: %s" % (request.request_type))
        
        with self.has_work_cond:
            # Add the request to the internal queue
            if request.request_type == "recv":
                with self.pending_requests_lock:
                    self.pending_requests.append(request)
                    self.pending_requests_has_work.set()
                    self.has_work_cond.notify() # We have the lock via caller and caller will release it later
                    Logger().debug("Notified self about has_work_cond during schedule_request")
            else:
                # If the request was outgoing we add to the out queue instead (on the out thread)
                self.network.t_out.add_out_request(request)
                
                #For synchronized sends we also need to add a recieve receipt request
                # FIXME: Implement here or in add_out_request

    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles, 
        logfiles and sockets. 

        Remember to always end your MPI program with this call. Otherwise proper 
        shutdown is not guaranteed. 
        """
        # Signal shutdown to the system (look in main while loop in
        # the run method)
        #Logger().debug("--- Calling shutdown ---")
        self.shutdown_event.set()
        
        # DEBUG
        #Logger().debug("--- Shutdown called, now for network finalizing --")
        # Sleeping here helps a lot but does not cure serious wounds
        #time.sleep(2)
        
        # We have now flushed all messages to the network layer. So we signal that it's time
        # to close
        #self.network.finalize()
        #Logger().debug("--- Network finally finalized --")

    @classmethod
    def initialized(cls):
        """
        Returns a boolean indicating whether the MPI environment is 
        initialized:: 

            from mpi import MPI

            status = MPI.initialized()  # status will be False
            mpi = MPI()

            status = MPI.initialized()  # status will now be True

        Please, if you're thinking of using this method, you might
        be down the wrong track. 
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
        # FIXME (doc)
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
        
        

