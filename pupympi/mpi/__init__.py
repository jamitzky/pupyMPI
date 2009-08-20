__version__ = 0.01


from optparse import OptionParser, OptionGroup
import threading
import sys, getopt, time

from mpi.communicator import Communicator
from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.tcp import TCPNetwork as Network

def flush_all():
    logger = Logger()

    for input in (sys.stdout, sys.stderr):
        try:
            input.flush()
            logger.debug("%s flushed" % input.name)
        except ValueError():
            logger.debug("Error in flushing %s" % input.name)

class MPI(threading.Thread):
    """
    This is the main class that contains most of the public API. Initializing 
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
        Initializes the MPI environment. This process will give each process 
        the rank and size in the MPI_COMM_WORLD communicator. This includes the
        rank and size of this, which and be read just after startup::

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

        options, args = parser.parse_args()
    
        mpi = MPI()
        mpi.startup(options, args)
        mpi.start()
        return mpi
    # }}}1

    def run(self):
        self.shutdown_lock = threading.Lock()

        # This can be moved out of there
        while True:
            if not self.shutdown_lock.acquire(False):
                print "Breaking"
                break
            self.shutdown_lock.release()

            # Continue with the stuff
            for comm in self.communicators:
                comm.update()
            
            # Trying to flush pipes
            flush_all()

            time.sleep(1)

    def startup(self, options, args): # {{{1
        print "Staring the MPI thread"
        # Initialise the logger
        logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)
        # Let the communication handle start up if it need to.

        logger.debug("Finished all the runtime arguments")
        self.MPI_COMM_WORLD = Communicator(options.rank, options.size, self)
        self.communicators = []
        self.communicators.append( self.MPI_COMM_WORLD )

        logger.debug("trying to start network")
        self.network = Network()
        self.network.run()
        logger.debug("Network started")

        all_procs = self.network.handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))
        self.MPI_COMM_WORLD.build_world( all_procs )
        logger.debug("Communicator started")

        user_options =[sys.argv[0], ] 
        user_options.append(sys.argv[sys.argv.index("--")+1:])

        sys.argv = user_options

        # Set a static attribute on the class so we know it's initialised.
        self.__class__.initialized = True
        logger.debug("Set the MPI environment to initialised")
    # }}}1

    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles, 
        logfiles and sockets. 

        FIXME: Should be manully try to kill some threads?
        """
        self.shutdown_lock.acquire()
        self.network.finalize()
        Logger().debug("Network finalized")

        # Trying to flush pipes
        flush_all()

    @classmethod
    def initialized(cls):
        """
        Returns a boolean indicating wheather the MPI environment is 
        initialized:: 

            from mpi import MPI

            status = MPI.initialized()  # status will be False
            mpi = MPI()

            status = MPI.initialized()  # status will now be True

        Please, if you're thinking of using this method, you might
        be down the wrong track. Don't write ugly code. 
        """
        return getattr(cls, '_initialized', False)
        
    #### Communicator creation, deletion
    def comm_create(self, arg):
        """
        This function creates a new communicator newcomm with communication group defined by group and a new context. No cached information propagates from comm to newcomm. The function returns MPI_COMM_NULL (None) to processes that are not in group. The call is erroneous if not all group arguments have the same value, or if group is not a subset of the group associated with comm. Note that the call is to be executed by all processes in comm, even if they do not belong to the new group. This call applies only to intra-communicators. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node102.html
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
        Logger().warn("Non-Implemented method 'comm_split' called.")
        
    def comm_compare(self, communicator1, communicator2):
        """
        MPI_IDENT results if and only if comm1 and comm2 are handles for the same object (identical groups and same contexts). MPI_CONGRUENT results if the underlying groups are identical in constituents and rank order; these communicators differ only by context. MPI_SIMILAR results if the group members of both communicators are the same but the rank order differs. MPI_UNEQUAL results otherwise. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node101.html#Node101
        """
        Logger().warn("Non-Implemented method 'comm_compare' called.")
        
        pass
