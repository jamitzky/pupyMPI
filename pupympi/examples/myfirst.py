import time
from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1


if rank == 0:
    neighbour = 1
    # Send
    print "Rank: %d sending to %d\n" % (rank,neighbour) 
    
    request = mpi.MPI_COMM_WORLD.isend(content, neighbour, DUMMY_TAG)
    request.wait()
    
    print "Rank: %d sent % s \n" % (rank, content) 

    
elif rank == 1: 
    neighbour = 0
    
    # Recieve
    print "Rank: %d recieving from %d\n" % (rank,neighbour)
    
    request = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request.wait()
    
    print "Rank: %d recieved %s\n" % (rank,recieved)
else:
    print "I'm rank %d and I'm not doing anything in this test\n" % rank


print "Done for rank %d\n" % rank


# Close the sockets down nicely
mpi.finalize()

