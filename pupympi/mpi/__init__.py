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
        from mpi.tcp import TCPNetwork as Network
        self.network = Network()
        
        self.MPI_COMM_WORLD = Communicator(rank, size, self)
        self.network = network = TCPNetwork()
        self.network.set_logger(logger)
        self.network.set_start_port( 14000 + rank )
        logger.debug("Network started")
        
        all_procs = self.network.handshake(mpi_run_hostname, mpi_run_port, rank)
        self.MPI_COMM_WORLD.build_world( all_procs )
        logger.debug("Communicator started")

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

    # Some wrapper methods
    def isend(*kargs, **kwargs):
        self.network.isend(*kargs, **kwargs)

    def send(*kargs, **kwargs):
        self.network.send(*kargs, **kwargs)

    def wait(*kargs, **kwargs):
        self.network.wait(*kargs, **kwargs)

    def recv(*kargs, **kwargs):
        self.network.recv(*kargs, **kwargs)

    def irecv(*kargs, **kwargs):
        self.network.irecv(*kargs, **kwargs)
