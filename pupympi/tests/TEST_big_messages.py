#!/usr/bin/env python2.6
# meta-description: tests how we deal with transmitting very large messages
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 25

from mpi import MPI
from mpi import constants
from mpi.exceptions import MPINoSuchRankException, MPIInvalidRangeException, MPIInvalidStrideException




mpi = MPI()


# we expect the group of MPI_COMM_WORLD to match with the communicator itself
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


#f = open("/tmp/mpi.big_messages.rank%s.log" % rank, "w")




# Test does not make sense for 1
assert size > 1

#### Setup prerequisites ####
FIRST_TAG = 111
SECOND_TAG = 222
THIRD_TAG = 333

#NOTE: Consider doing this with other data structures for realism
string = "abcdefghijklmnopqrst" # 20 chars

largeMsg = 256*string
largerMsg = 1024*string
heftyMsg = 1024*1024*string
# You can make a string longer than this but python (pickle) gets in trouble, you can't repr it and it takes up a lot of RAM :)
# max for python2.5 on my machine is about 350*1024*1024 .. let's stay below that

# 0 send, 1 recives, the rest do nothing
if rank == 0:
    mpi.MPI_COMM_WORLD.send(1,largeMsg,FIRST_TAG)
    #mpi.MPI_COMM_WORLD.send(1,("test",4),FIRST_TAG) # Fails when some debug line tries to string convert the tuple
    mpi.MPI_COMM_WORLD.send(1,largerMsg,SECOND_TAG)
    mpi.MPI_COMM_WORLD.send(1,heftyMsg,THIRD_TAG)    
    #DEBUG
    print "msgs sent"    
elif rank == 1:
    msg = mpi.MPI_COMM_WORLD.recv(0,FIRST_TAG)
    assert msg == largeMsg
    
    msg = mpi.MPI_COMM_WORLD.recv(0,SECOND_TAG)
    assert msg == largerMsg

    msg = mpi.MPI_COMM_WORLD.recv(0,THIRD_TAG)
    assert msg == heftyMsg
    assert len(msg) == 1024*1024*20 # Check that stuff isn't mangled
    #print str(len(msg) == 1024*1024*20)
    
else:
    pass

#### Test message passing ####


#f.write( "Done for rank %d\n" % rank)

#f.flush()
#f.close()

# Close the sockets down nicely
mpi.finalize()
