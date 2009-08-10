# Fred dabbling in communication

class Communicator():
    def __init__(self, rank, size, mpi_instance, name="MPI_COMM_WORLD"):
        self.rank = rank
        self.size = size
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
        return self.members[rank]
    
    def rank(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.rank

    def size(self, comm=None):
        if not comm:
            comm = self.MPI_COMM_WORLD
        return comm.size

    def get_name(self):
        return self.name
    
    
