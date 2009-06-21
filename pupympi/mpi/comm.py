class Communicator():
    def __init__(self, rank, size, name="MPI_COMM_WORLD"):
        self.rank = rank
        self.size = size
        self.name = name

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)
