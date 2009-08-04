# Fred dabbling in communication

class Communicator():
    def __init__(self, rank, size, name="MPI_COMM_WORLD"):
        self.rank = rank
        self.size = size
        self.name = name
        
        # List of process-members of the communicator
        processList = []
        for i in range(size):
            # Tuple describing a process
            # is (address,port,status)
            processList += [(None,None,None)] # appending here preserves indexing=order=rank
            

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

    def have_rank(self, rank):
        return rank in self.members
    
    
    
