__version__ = 0.01

from mpi.communicator import Communicator
from mpi.logger import Logger
from mpi.tcp import TCPNetwork as Network
import threading
import sys, getopt

class MPI:

    def __init__(self):
        try:
            optlist, args = getopt.gnu_getopt(sys.argv[1:], 'dv:ql:s:r:', ['verbosity=','quiet','log-file=','debug','size=','rank=','network-type=','port=','mpirun-conn-port=', 'mpirun-conn-host='])
        except getopt.GetoptError, err:
            print str(err)

        debug = False
        verbosity = 1
        quiet = False
        rank = 0
        size = 0
        hostname = None
        port = None
        
        logfile = None
        
        for opt, arg in optlist:
            if opt in ("-d", "--debug"):
                debug = True

            if opt in ("-v", "--verbosity"):
                verbosity = int(arg)

            if opt in ("-q", "--quiet"):
                quiet = True

            if opt in ("-l", "--log-file"):
                logfile = arg

            if opt in ("-r", "--rank"):
                try:
                    rank = int(arg)
                except ValueError:
                    pass
            if opt in ("-s", "--size"):
                try:
                    size = int(arg)
                except:
                    pass
                
            if opt == "--mpirun-conn-host":
                mpi_run_hostname = arg
            if opt == "--mpirun-conn-port":
                mpi_run_port = int(arg)

        # Initialise the logger
        logger = Logger(logfile or "mpi", "proc-%d" % rank, debug, verbosity, quiet)
        # Let the communication handle start up if it need to.

        logger.debug("Finished all the runtime arguments")
        
        self.MPI_COMM_WORLD = Communicator(rank, size, self)
        #Trying threading
        #from mpi.tcp import ThreadTCPNetwork as ThreadNetwork
        #logger.debug("trying to start network")
        #self.network = ThreadNetwork().start()

        from mpi.tcp import TCPNetwork as Network
        logger.debug("trying to start network")
        self.network = Network()
        logger.debug("Network started")

        all_procs = self.network.handshake(mpi_run_hostname, mpi_run_port, rank)
        self.MPI_COMM_WORLD.build_world( all_procs )
        logger.debug("Communicator started")

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
