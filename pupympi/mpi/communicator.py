# Fred dabbling in communication
from mpi.exceptions import MPINoSuchRankException
from mpi.logger import Logger

class Communicator:
    def __init__(self, rank, size, mpi_instance, name="MPI_COMM_WORLD"):
        self._rank = rank
        self._size = size
        self.name = name
        self.members = {}
        self.attr = {}
        if name == "MPI_COMM_WORLD":
            self.attr = {   "MPI_TAG_UB": 2**30, \
                            "MPI_HOST": "TODO", \
                            "MPI_IO": rank, \
                            "MPI_WTIME_IS_GLOBAL": False
                        }
    
    def build_world(self, all_procs):
        logger = Logger()
        for (hostname, port_no, rank) in all_procs:
            self.members[ rank ] = (hostname, port_no)
            logger.debug("Added proc-%d with info (%s,%s) to the world communicator" % (rank, hostname, port_no))

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

    def have_rank(self, rank):
        return rank in self.members
    
    def get_network_details(self, rank):
        if not self.have_rank(rank):
            raise MPINoSuchRankException()

        return self.members[rank]
    
    def rank(self):
        return self._rank

    def size(self):
        return self._size

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    # TODO: may want to drop this and simply allow users access to the underlying dict?
    # TODO: Global fixed keys (http://www.mpi-forum.org/docs/mpi-11-html/node143.html) should be defined?
    def attr_get(self, key):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html, python-style:
        keyval is now any immutable datatype, and flag is not used. If the key is not defined, None is returned. """
        return self.attr[key]
    def attr_put(self, key, value):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html"""
        self.attr[key] = value        
