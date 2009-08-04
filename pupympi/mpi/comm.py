class Communicator():
    def __init__(self, rank, size, mpi_instance, name="MPI_COMM_WORLD"):
        self.rank = rank
        self.size = size
        self.name = name
        self.mpi_instance = mpi_instance

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

    def have_rank(self, rank):
        return rank in self.members
