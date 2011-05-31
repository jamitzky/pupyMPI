#!/usr/bin/env python2.6
# meta-description: Test basic immediate communication. First rank 0 isends timestamp to rank 1 who is a very slow reciever so rank 0 should quit early
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1

f = open(constants.DEFAULT_LOGDIR+"mpi.simple_immediate_sr.rank%s.log" % rank, "w")

if rank == 0:
    neighbour = 1
    # Send
    f.write("Rank: %d sending to %d\n" % (rank,neighbour) )
    f.flush()
    
    request = mpi.MPI_COMM_WORLD.isend(content, neighbour, DUMMY_TAG)
    request.wait()
    
    f.write("Rank: %d sent % s \n" % (rank, content) )
    f.flush()

    
elif rank == 1: 
    neighbour = 0
    
    # Recieve
    f.write("Rank: %d recieving from %d\n" % (rank,neighbour))
    f.flush()
    
    request = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request.wait()
    
    f.write("Rank: %d recieved %s\n" % (rank,recieved))
    f.flush()
else:
    f.write("I'm rank %d and I'm not doing anything in this test\n" % rank)
    f.flush()

f.write("Done for rank %d\n" % rank)
f.flush()
f.close()


# Close the sockets down nicely
mpi.finalize()
