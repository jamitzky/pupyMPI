#!/usr/bin/env python2.6
# meta-description: Test out of order immediate sending/receiving between 2 processses
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 15

from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content1 = "This is message one"
content2 = "This is message two"
content3 = "This is message three"

FIRST_TAG = 111
SECOND_TAG = 222
THIRD_TAG = 333

# Log stuff so progress is easier followed
#f = open(constants.LOGDIR+"mpi.isend_to_irecv.rank%s.log" % rank, "w")

# Rank 0 posts isends and irecvs in order and waits in reverse order
if rank == 0:
    neighbour = 1

    sendRequest1 = mpi.MPI_COMM_WORLD.isend(content1, neighbour, FIRST_TAG)    
    sendRequest2 = mpi.MPI_COMM_WORLD.isend(content2, neighbour, SECOND_TAG)    
    sendRequest3 = mpi.MPI_COMM_WORLD.isend(content3, neighbour, THIRD_TAG)    

    recvRequest1 = mpi.MPI_COMM_WORLD.irecv(neighbour,FIRST_TAG)
    recvRequest2 = mpi.MPI_COMM_WORLD.irecv(neighbour,SECOND_TAG)
    recvRequest3 = mpi.MPI_COMM_WORLD.irecv(neighbour,THIRD_TAG)
    
    #f.write("Rank %i, done requesting" % rank)
    
    recvRes3 = recvRequest3.wait()
    recvRes2 = recvRequest2.wait()
    recvRes1 = recvRequest1.wait()
    
    #f.write("Recieved %s, %s, %s - rank %i" % (recvRes3, recvRes2, recvRes1, rank))
    
    sendRequest3.wait()
    sendRequest2.wait()
    sendRequest1.wait()

    #f.write("Rank %i, done waiting for sends" % rank)
    
    assert recvRes1 == content1
    assert recvRes2 == content2
    assert recvRes3 == content3

# Rank 1 just mixes stuff up like crazy
elif rank == 1:
    neighbour = 0

    recvRequest2 = mpi.MPI_COMM_WORLD.irecv(neighbour,SECOND_TAG)        

    sendRequest2 = mpi.MPI_COMM_WORLD.isend(content2, neighbour, SECOND_TAG)
    sendRequest2.wait()

    recvRequest3 = mpi.MPI_COMM_WORLD.irecv(neighbour,THIRD_TAG)
    
    sendRequest3 = mpi.MPI_COMM_WORLD.isend(content3, neighbour, THIRD_TAG)    

    recvRequest1 = mpi.MPI_COMM_WORLD.irecv(neighbour,FIRST_TAG)
    recvRes1 = recvRequest1.wait()

    recvRes3 = recvRequest3.wait()

    sendRequest1 = mpi.MPI_COMM_WORLD.isend(content1, neighbour, FIRST_TAG)    
    
    recvRes2 = recvRequest2.wait()
    
    #f.write("Rank %i, done requesting" % rank)
    

    #f.write("Recieved %s, %s, %s - rank %i" % (recvRes1, recvRes3, recvRes2, rank))
    
    sendRequest1.wait()
    sendRequest2.wait()

    #f.write("Rank %i, done waiting for sends" % rank)

    assert recvRes1 == content1
    assert recvRes2 == content2
    assert recvRes3 == content3
    
else: 
    pass


#f.write( "Done for rank %d\n" % rank)
#f.flush()
#f.close()

# Close the sockets down nicely
mpi.finalize()
