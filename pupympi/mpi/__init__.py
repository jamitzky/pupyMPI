__version__ = 0.01

from mpi.comm3 import Communicator

class MPI:

    def __init__(self):
        import sys, getopt
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
        from mpi.logger import setup_log
        logger = setup_log(logfile or "mpi", "proc-%d" % rank, debug, verbosity, quiet)
        self.logger = logger
        
        # Let the communication handle start up if it need to.
        from mpi.tcp import TCPNetwork
        
        logger.debug("Starting the network")
        
        self.MPI_COMM_WORLD = Communicator(rank, size, self)
        self.network = network = TCPNetwork(self)
        self.network.handshake(mpi_run_hostname, mpi_run_port)

    def rank(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.rank

    def size(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.size
    
    def finalize(self):
        self.network.finalize()
