__version__ = 0.01

from optparse import OptionParser, OptionGroup
import threading
import sys, getopt

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.tcp import TCPNetwork as Network

class MPI:

    def __init__(self):
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
        ##Trying threading
        #from mpi.tcp import ThreadTCPNetwork as Network
        #logger.debug("trying to start network")
        #self.network = Network().start()

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
        logger = Logger()
        self.network.finalize()
        logger.debug("Network finalized")

    def _ensure_comm(self, comm):
        return comm or self.MPI_COMM_WORLD

    @classmethod
    def initialized(cls):
        return getattr(cls, '_initialized', False)

    # Some wrapper methods
    def isend(self, destination, content, tag, comm=None):
        comm = self._ensure_comm(comm)
        return self.network.isend(destination, content, tag, comm)

    def send(self, destination, content, tag, comm=None):
        comm = self._ensure_comm(comm)
        return self.network.send(destination, content, tag, comm)

    def wait(self, handle):
        Logger().warn("Non-Implemented method 'wait' called.")
        return self.network.wait(handle)
        
    def barrier(self, comm=None):
        comm = self._ensure_comm(comm)
        Logger().warn("Non-Implemented method 'Barrier' called.")
        return self.network.barrier(comm)

    def recv(self, destination, tag, comm=None):
        comm = self._ensure_comm(comm)
        return self.network.recv(destination, tag, comm)

    def irecv(self, destination, tag, comm=None):
        comm = self._ensure_comm(comm)
        return self.network.irecv(destination, tag, comm)
