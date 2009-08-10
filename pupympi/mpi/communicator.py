# Fred dabbling in communication
from mpi.exceptions import MPINoSuchRankException

class Communicator():
    def __init__(self, rank, size, mpi_instance, name="MPI_COMM_WORLD"):
        self._rank = rank
        self._size = size
        self.name = name
        self.members = {}
        self.logger = mpi_instance.logger
    
    def build_world(self, all_procs):
        for (hostname, port_no, rank) in all_procs:
            self.members[ rank ] = (hostname, port_no)
            self.logger.debug("Added proc-%d with info (%s,%s) to the world communicator" % (rank, hostname, port_no))

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
