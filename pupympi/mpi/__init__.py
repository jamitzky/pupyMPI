__version__ = 0.01

from mpi.comm import Communicator

class MPI:

    def __init__(self):
        import sys, getopt
        try:
            optlist, args = getopt.gnu_getopt(sys.argv[1:], 'dv:ql:s:r:', ['verbosity=','quiet','log-file=','debug','size=','rank=','network-type=','port='])
        except getopt.GetoptError, err:
            print str(err)

        debug = False
        verbosity = 1
        quiet = False
        rank = 0
        size = 0
        network_type = "tcp"
        port = 0
        
        logfile = None

        for opt, arg in optlist:
            if opt in ("-d", "--debug"):
                debug = True

            if opt in ("-v", "--verbosity"):
                verbosity = arg

            if opt in ("-q", "--quiet"):
                quiet = True

            if opt in ("-l", "--log-file"):
                logfile = arg

            if opt in ("-r", "--rank"):
                try:
                    rank = int(arg)
                except ValueError:
                    pass
            if opt == "--network-type":
                if arg in ('tcp', ):
                    network_type = arg

            if opt in ("-s", "--size"):
                try:
                    size = int(arg)
                except:
                    pass
                
            if opt == "--port":
                port = int(arg)

        # Let the communication handle start up if it need to.
        if network_type == "tcp":
            from mpi.tcp import TCPNetwork
            self.network = network = TCPNetwork(port)

        self.MPI_COMM_WORLD = Communicator(rank, size)

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
