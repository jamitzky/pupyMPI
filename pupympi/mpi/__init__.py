__version__ = 0.2 # It bumps the version or else it gets the hose again!

from optparse import OptionParser, OptionGroup
import threading, sys, getopt, time
from threading import Thread

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.network.tcp import TCPNetwork as Network
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
    
    def version_check(self):
        """
        Check that the required Python version is installed
        """
        (major,minor,_,_,_) = sys.version_info
        if (major == 2 and minor < 6) or major < 2:
            Logger().error("pupyMPI requires Python 2.6 (you may have to kill processes manually)")
            sys.exit(1)
        elif major >= 2 and minor is not 6:
            Logger().warn("pupyMPI is only certified to run on Python 2.6")


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

        #logger.debug("Finished all the runtime arguments")

        # First check for required Python version
        self.version_check()

        # Starting the network.
        # NOTE: This is probably a TCP network, but it can be 
        # replaced pretty easily if we want to. 
        self.network = Network(options)
        
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
        self.network.set_mpi_world( self.MPI_COMM_WORLD )
        
        # Set the default receive callback for handling those 
        # receives. 
        self.network.register_callback("recv", self.recv_callback)

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

        self.daemon = True
        self.start()
        
        # Initialising data structures for staring jobs.
        self.unstarted_requests = []
        self.unstarted_requests_lock = threading.Lock()
        self.unstarted_requests_has_work = threading.Event()
        
        self.pending_requests = []
        self.pending_requests_lock = threading.Lock()
        self.pending_requests_has_work = threading.Event()
        
        self.has_work_cond = Threading.Condition()

        self.shutdown_event = threading.Event()

    def run(self):

        while not self.shutdown_event.is_set():
            with self.has_work_cond:
                self.has_work_cond.wait()
                
                if self.pending_requests_has_work.is_set():
                    with self.pending_requests_lock:
                        for request in self.pending_requests:
                            # Handle the actual request
                            pass
                        self.pending_requests_has_work.clear()
                    
                if self.unstarted_requests_has_work.is_set():
                    with self.unstarted_requests_lock:
                        for request in self.unstarted_requests:
                            self.unstarted_requests.remove(request)
                            # Add the request
                        self.unstarted_requests_has_work.clear()
                            

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
        #Logger().debug("Network finalized")
        
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
