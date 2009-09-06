__version__ = 0.01 # It bumps the version or else it gets the hose again!

from optparse import OptionParser, OptionGroup
import threading, sys, getopt, time

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.network.tcp import TCPNetwork as Network

class MPI(threading.Thread):
    """
    This is the main class containing most of the public API. Initializing 
    the MPI system is done by creating an instance of this class. Through a
    MPI instance a program can interact with other processes through different
    communicators. 

    NOTE: The MPI instance state is a static class variable, so creating multiple
    instances will always yield 'the same' instance, much like a singleton design
    pattern. 
    """

    @classmethod
    def initialize(cls): # {{{1
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

        options, args = parser.parse_args()
    
        mpi = MPI()
        mpi.shutdown_lock = threading.Lock()
        mpi.shutdown_lock.acquire()
        try:
            mpi.startup(options, args)
        except:
            print "Horrible failure in MPI startup, bailing out!"
            sys.exit(200)
        mpi.daemon = True
        mpi.start()
        return mpi
    # }}}1

    def run(self):
        # This can be moved out of there
        while True:

            # Check for shutdown
            if self.shutdown_lock.acquire(False):
                self.shutdown_lock.release()
                break

            # Update request objects
            for comm in self.communicators:
                comm.update()                
            
            time.sleep(1)

    def recv_callback(self, *args, **kwargs):
        Logger().debug("MPI layer recv_callback called")

    def startup(self, options, args): # {{{1
        # FIXME: This should be moved to the __init__ method
        
        # Initialise the logger
        logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)
        # Let the communication handle start up if it need to.

        logger.debug("Finished all the runtime arguments")
        logger.debug("Currently active threads: %d. This is daemon? %s" % (threading.activeCount(), "NOT IMPLEMENTED"))

        # Starting the network. This is probably a TCP network, but it can be 
        # replaced pretty easily if we want to. 
        self.network = Network(options)

        # Create the initial communicator MPI_COMM_WORLD. It's initialized with 
        # the rank of the process that holds it and size.
        # The members are filled out after the network is initialized.
        self.MPI_COMM_WORLD = Communicator(options.rank, options.size, self.network)
        self.communicators = []
        self.communicators.append( self.MPI_COMM_WORLD )

        # Tell the communicator to build it's "world" from the results of the network
        # initialization. All network types will create a variable called all_procs
        # containing network specific information for all ranks.
        self.MPI_COMM_WORLD.build_world( self.network.all_procs )

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

        # Set a static attribute on the class so we know it's initialised.
        self.__class__._initialized = True
        logger.debug("Set the MPI environment to initialised")
    # }}}1

    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles, 
        logfiles and sockets. 

        FIXME: Should we manually try to kill some threads?
        """
        # Wait for shutdown to be signalled
        self.shutdown_lock.release()
        # Shutdown the network
        self.network.finalize()
        Logger().debug("Network finalized")

        # Trying to flush pipes
        flush_all()

    @classmethod
    def initialized(cls):
        """
        Returns a boolean indicating whether the MPI environment is 
        initialized:: 

            from mpi import MPI

            status = MPI.initialized()  # status will be False
            mpi = MPI.initialize()

            status = MPI.initialized()  # status will now be True

        Please, if you're thinking of using this method, you might
        be down the wrong track. Don't bend the Python like Bromer does. 
        """
        return getattr(cls, '_initialized', False)
        
    #### Communicator creation, deletion
    def comm_create(self, group, arg):
        """
        This function creates a new communicator newcomm with communication group defined by group and a new context. No cached information propagates from comm to newcomm. The function returns MPI_COMM_NULL (None) to processes that are not in group. The call is erroneous if not all group arguments have the same value, or if group is not a subset of the group associated with comm. Note that the call is to be executed by all processes in comm, even if they do not belong to the new group. This call applies only to intra-communicators. 
        [ IN comm] communicator (handle)
        [ IN group] Group, which is a subset of the group of comm (handle)
        [ OUT newcomm] new communicator (handle)
        
        http://www.mpi-forum.org/docs/mpi-11-html/node102.html
        
        This call is currently implemented locally only.
        """
        Logger().warn("Non-Implemented method 'comm_create' called.")
        

    def comm_free(self, existing_communicator):
        """
        This collective operation marks the communication object for deallocation. The handle is set to MPI_COMM_NULL. Any pending operations that use this communicator will complete normally; the object is actually deallocated only if there are no other active references to it. This call applies to intra- and inter-communicators. The delete callback functions for all cached attributes (see section Caching ) are called in arbitrary order.
    
        http://www.mpi-forum.org/docs/mpi-11-html/node103.html#Node103
        """
        Logger().warn("Non-Implemented method 'comm_free' called.")


    def comm_split(self, existing_communicator, color = None, key = None):
        """
        FIXME
        """
        Logger().warn("Non-Implemented method 'comm_split' called.")

    def comm_dup(self, todo_args_missing):
        """
        FIXME
        """
        Logger().warn("Non-Implemented method 'comm_dup' called.")
        
    def comm_compare(self, communicator1, communicator2):
        """
        MPI_IDENT results if and only if comm1 and comm2 are handles for the same object (identical groups and same contexts). MPI_CONGRUENT results if the underlying groups are identical in constituents and rank order; these communicators differ only by context. MPI_SIMILAR results if the group members of both communicators are the same but the rank order differs. MPI_UNEQUAL results otherwise. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node101.html#Node101
        """
        Logger().warn("Non-Implemented method 'comm_compare' called.")
        
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
