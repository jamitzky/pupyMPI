#!/usr/bin/env python
# meta-description: Tests how we deal with transmitting very large messages
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 60

# NOTE: You do not want to call this test with debugging (that prints the message content) active!
# Outputting the big messages take a _long_ time

from mpi import MPI
from mpi import constants

mpi = MPI()

# we expect the group of MPI_COMM_WORLD to match with the communicator itself
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

# Log stuff so progress is easier followed
f = open(constants.DEFAULT_LOGDIR+"mpi.big_messages.rank%s.log" % rank, "w")

# Test does not make sense for 1
assert size > 1

#### Setup prerequisites ####
FIRST_TAG = 111
SECOND_TAG = 222
THIRD_TAG = 333

string = "abcdefghijklmnopqrst" # 20 chars

largeMsg = 256*string
largerMsg = 1024*string
heftyMsg = 1024*1024*string
# You can make a string longer than this but python (pickle) gets in trouble, you can't repr it and it takes up a lot of RAM :)
# max for python2.5 on my machine is about 350*1024*1024 chars.. let's stay below that

#### Test message passing ####

# One way comm: 0 sends, 1 recives, the rest do nothing
if rank == 0:
    mpi.MPI_COMM_WORLD.send(largeMsg, 1, FIRST_TAG)
    mpi.MPI_COMM_WORLD.send(largerMsg, 1, SECOND_TAG)
    mpi.MPI_COMM_WORLD.send(heftyMsg, 1, THIRD_TAG)    
    f.write( "Done sending big messages - rank %d\n" % rank)
    f.flush()
elif rank == 1:
    msg = mpi.MPI_COMM_WORLD.recv(0,FIRST_TAG)
    assert msg == largeMsg
    
    msg = mpi.MPI_COMM_WORLD.recv(0,SECOND_TAG)
    assert msg == largerMsg

    msg = mpi.MPI_COMM_WORLD.recv(0,THIRD_TAG)
    assert msg == heftyMsg
    assert len(msg) == 1024*1024*20 # Check actual length
    f.write( "Recieved all three big messages - rank %d\n" % rank)
    f.flush()    
else:
    pass


# Two way comm blocking
if rank == 0:
    mpi.MPI_COMM_WORLD.send(largerMsg, 1, SECOND_TAG)

    msg = mpi.MPI_COMM_WORLD.recv(1,THIRD_TAG)
    assert msg == heftyMsg
    
    msg = mpi.MPI_COMM_WORLD.recv(1,SECOND_TAG)
    assert msg == largerMsg

    mpi.MPI_COMM_WORLD.send(heftyMsg, 1, THIRD_TAG)
    
    f.write( "Blocking two-way passing of big messages done - rank %d\n" % rank)
    f.flush()
    
elif rank == 1:
    msg = mpi.MPI_COMM_WORLD.recv(0,SECOND_TAG)
    assert msg == largerMsg

    mpi.MPI_COMM_WORLD.send(heftyMsg, 0, THIRD_TAG)    
    mpi.MPI_COMM_WORLD.send(largerMsg, 0, SECOND_TAG)

    msg = mpi.MPI_COMM_WORLD.recv(0,THIRD_TAG)
    assert msg == heftyMsg

    f.write( "Blocking two-way passing of big messages done - rank %d\n" % rank)
    f.flush()
else:
    pass


# Two way comm immediate
if rank == 0:
    s1 = mpi.MPI_COMM_WORLD.isend(largerMsg, 1, SECOND_TAG)
    s2 = mpi.MPI_COMM_WORLD.isend(heftyMsg, 1, THIRD_TAG)
    
    f.write( "Immediate send done - rank %d\n" % rank)
    f.flush()
    
    r1 = mpi.MPI_COMM_WORLD.irecv(1,SECOND_TAG)
    r2 = mpi.MPI_COMM_WORLD.irecv(1,THIRD_TAG)
        
    recieve1 = r1.wait()
    recieve2 = r2.wait()

    f.write( "Recv wait done - rank %d\n" % rank)
    f.flush()
    
    assert recieve1 == largerMsg
    assert recieve2 == heftyMsg

    s1.wait()
    s2.wait()

    f.write( "Send wait done - rank %d\n" % rank)
    f.flush()   
elif rank == 1:
    s1 = mpi.MPI_COMM_WORLD.isend(largerMsg, 0, SECOND_TAG)
    s2 = mpi.MPI_COMM_WORLD.isend(heftyMsg, 0, THIRD_TAG)
    
    f.write( "Immediate send done - rank %d\n" % rank)
    f.flush()
    
    r1 = mpi.MPI_COMM_WORLD.irecv(0,SECOND_TAG)
    r2 = mpi.MPI_COMM_WORLD.irecv(0,THIRD_TAG)
    
    recieve1 = r1.wait()
    recieve2 = r2.wait()

    f.write( "Recv wait done - rank %d\n" % rank)
    f.flush()
    
    assert recieve1 == largerMsg
    assert recieve2 == heftyMsg

    s1.wait()
    s2.wait()

    f.write( "Send wait done - rank %d\n" % rank)
    f.flush()

else:
    pass


f.write( "Done for rank %d\n" % rank)
f.flush()
f.close()

# Close the sockets down nicely
mpi.finalize()
