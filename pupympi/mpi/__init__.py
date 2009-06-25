__version__ = 0.01

from mpi.comm import Communicator

class MPI:

    def __init__(self):
        print "got init"
        import sys, getopt
        try:
            optlist, args = getopt.gnu_getopt(sys.argv[1:], 'dv:ql:s:r:', ['verbosity=','quiet','log-file=','debug','size=','rank='])
        except getopt.GetoptError, err:
            print str(err)

        debug = False
        verbosity = 1
        quiet = False
        rank = 0
        size = 0

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

            if opt in ("-s", "--size"):
                try:
                    size = int(arg)
                except:
                    pass

        self.config = {'size' : size, 'rank' : rank, 'debug' : debug, 'verbosity' : verbosity, 'quiet' : quiet, 'logfile' : logfile }

        self.MPI_COMM_WORLD = Communicator(rank, size)

    def rank(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.rank

    def size(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.size
