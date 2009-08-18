__version__ = 0.01

from optparse import OptionParser, OptionGroup
import threading
import sys, getopt

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.tcp import TCPNetwork as Network

class MPI:
    """
    This is the main class that contains most of the public API. Initializing 
    the MPI system is done by creating an instance of this class. Through a
    MPI instance a program can interact with other processes through different
    communicators. 

    NOTE: The MPI instance state is a static class variable, so creating multiple
    instances will always yield 'the same' instance, much like a singleton design
    pattern. 
    """

    def __init__(self):
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

        # Initialise the logger
        logger = Logger(options.logfile, "proc-%d" % options.rank, options.debug, options.verbosity, options.quiet)
        # Let the communication handle start up if it need to.

        logger.debug("Finished all the runtime arguments")
        self.MPI_COMM_WORLD = Communicator(options.rank, options.size, self)
        #Trying threading
        #from mpi.tcp import ThreadTCPNetwork as ThreadNetwork
        #logger.debug("trying to start network")
        #self.network = ThreadNetwork().start()

        from mpi.tcp import TCPNetwork as Network
        logger.debug("trying to start network")
        self.network = Network()
        logger.debug("Network started")

        all_procs = self.network.handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))
        self.MPI_COMM_WORLD.build_world( all_procs )
        logger.debug("Communicator started")

        import sys
        user_options =[sys.argv[0], ] 
        user_options.append(sys.argv[sys.argv.index("--")+1:])

        sys.argv = user_options

        # Set a static attribute on the class so we know it's initialised.
        self.__class__._initialized = True
        logger.debug("Set the MPI environment to initialised")

    def finalize(self):
        """
        This method cleans up after a MPI run. Closes filehandles, 
        logfiles and sockets. 
        """
        logger = Logger()
        self.network.finalize()
        logger.debug("Network finalized")

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

    # Some wrapper methods
    def isend(self, destination, content, tag, comm=None):
        """
        document me
        """
        comm = self._ensure_comm(comm)
        return self.network.isend(destination, content, tag, comm)

    def send(self, destination, content, tag, comm=None):
        """
        document me
        """
        request = self.isend(destination, content, tag, comm)
        return request.wait()

    def barrier(self, comm=None):
        """
        document me
        """
        comm = self._ensure_comm(comm)
        Logger().warn("Non-Implemented method 'Barrier' called.")
        return self.network.barrier(comm)

    def recv(self, destination, tag, comm=None):
        """
        document me
        """
        request = self.irecv(destination, tag, comm)
        return request.wait()

    def irecv(self, destination, tag, comm=None):
        """
        document me
        """
        comm = self._ensure_comm(comm)
        return self.network.irecv(destination, tag, comm)
