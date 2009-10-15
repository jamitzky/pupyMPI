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

        options, args = parser.parse_args()
    
        # Initialise the logger
        logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)

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
        
        # Set the default receive callback for handling those 
        # receives. 
        self.network.t_in.register_callback("recv", self.recv_callback)

        # Change the contents of sys.argv runtime, so the user processes 
        # can't see all the mpi specific junk parameters we start with.
        user_options =[sys.argv[0], ] 
        user_options.append(sys.argv[sys.argv.index("--")+1:])
        sys.argv = user_options

        # Set a static attribute on the class so we know it is initialised.
        self.__class__._initialized = True
        #logger.debug("Set the MPI environment to initialised")
        
        # set up 'constants'
        constants.MPI_GROUP_EMPTY = Group()
        
        # Initialising data structures for staring jobs.
        self.unstarted_requests = []
        self.unstarted_requests_lock = threading.Lock()
        self.unstarted_requests_has_work = threading.Event()
        
        self.pending_requests = []
        self.pending_requests_lock = threading.Lock()
        self.pending_requests_has_work = threading.Event()
        
        self.has_work_cond = Threading.Condition()

        self.shutdown_event = threading.Event()
        
        # Adding locks and initial information about the request queue
        self.current_request_id_lock = threading.Lock()
        self.current_request_id = 0
        
        # Locks, events, queues etc for handling the raw data the network
        # passes to this thread
        self.raw_data_queue = []
        self.raw_data_lock = threading.Lock()
        self.raw_data_event = threading.Event()
        
        # Locks, queues etc for handling the reived data. There are no
        # events as this is handled through the "pending_request_" event.
        self.received_data = []
        self.received_data_lock = threading.Lock()
        
        self.daemon = True
        self.start()

    def match_pending(self, request):
        """
        Tries to match a pending request with something in
        the received data.
        """
        pass

    def run(self):

        while not self.shutdown_event.is_set():
            with self.has_work_cond:
                self.has_work_cond.wait()
                
                if self.unstarted_requests_has_work.is_set():
                    with self.unstarted_requests_lock:
                        for request in self.unstarted_requests:
                            self.unstarted_requests.remove(request)
                            self.schedule_request(request)
                            
                        self.unstarted_requests_has_work.clear()
                
                if self.raw_data_event.is_set():
                    with self.raw_data_lock:
                        with self.received_data_lock:
                            for raw_data in self.raw_data_queue:
                                data = pickle.loads(raw_data)
                                self.received_data.append(data)
                                self.pending_requests_has_work.set()
                        self.raw_data_event.clear()
                        
                # Think about optimal ordering
                if self.pending_requests_has_work.is_set():
                    with self.pending_requests_lock:
                        for request in self.pending_requests:
                            self.match_pending(request)

                        self.pending_requests_has_work.clear()
                    
                            
    def schedule_request(self, request):
        # If we have a request object we might already have received the
        # result. So we look into the internal queue to see. If so, we use the
        # network_callback method to update all the internal structure.
        if request.request_type == 'recv':
            data = self.pop_unhandled_message(participant, tag)
            if data:                
                Logger().debug("Unhandled message had data") # DEBUG: This sometimes happen in TEST_cyclic
                request.network_callback(lock=False, status="ready", data=data['data'], ffrom="Right-away-quick-fast-receive")
                return

        # Add the request to the internal queue
        with self.pending_requests_lock:
            self.pending_requests.append(request)
            self.pending_requests_has_work.set()
            self.has_work_cond.notify()

        # Start the network layer on a job as well
        self.network.add_request(request)

    def remove_pending_request(self, request):
        with self.pending_requests_lock:
            self.pending_requests.remove(request)
            
        # FIXME: Remove this from the network layout mapping
        # asssss well. 

    # FIXME: JUST MOVED FROM COMMUNICATOR
    def pop_unhandled_message(self, participant, tag):
        self.unhandled_messages_lock.acquire()
        try:
            package = self.unhandled_receives[tag][participant].pop(0)
            self.unhandled_messages_lock.release()
            return package
        except (IndexError, KeyError):
            pass
        self.unhandled_messages_lock.release()
    
    # FIXME: JUST MOVED FROM COMMUNICATOR
    def handle_receive(self, communicator=None, tag=None, data=None, sender=None, recv_type=None):
        # Look for a request object right now. Otherwise we just put it on the queue and let the
        # update handler do it.
        
        # Put it on unhandled requests
        if tag not in self.unhandled_receives:
            self.unhandled_receives[tag] = {}
            
        if not sender in self.unhandled_receives[tag]:
            self.unhandled_receives[tag][sender] = []

        self.unhandled_receives[tag][sender].append( {'data': data, 'recv_type' : recv_type })
        
        Logger().info("Added unhandled data with tag(%s), sender(%s), data(%s), recv_type(%s)" % (tag, sender, data, recv_type))
        self.update()


    def recv_callback(self, *args, **kwargs):
        #Logger().debug("MPI layer recv_callback called")
        
        if "communicator" in kwargs:
            self.communicators[ kwargs['communicator'] ].handle_receive(*args, **kwargs)
        
    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles, 
        logfiles and sockets. 

        Remember to always end your MPI program with this call. Otherwise proper 
        shutdown is not guaranteed. 
        """
        # Signal shutdown to the system (look in main while loop in
        # the run method)
        self.shutdown_event.set()

        # Shutdown the network
        self.network.finalize()
        
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
        
        

