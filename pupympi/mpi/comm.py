class Communicator():
    def __init__(self, rank, size, process_placeholder, name="MPI_COMM_WORLD"):
        self.rank = rank
        self.size = size
        self.name = name
        self.members = {}

        # Initialize the list with other processes
        for (rank, process) in process_placeholder['all']:
            self.members[rank] = process

        self.ego = process_placeholder['self']

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

