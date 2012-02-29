#!/usr/bin/env python
# meta-description: Test socket pool where connections are replaced since rank 0 has to send to more procs than pool allows
# meta-expectedresult: 0
# meta-minprocesses: 7
# meta-socket-pool-size: 5

from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1

#f = open(constants.DEFAULT_LOGDIR+"mpi.socket_pool_replace.rank%s.log" % rank, "w")

neighbours = range(size)

if rank == 0: # rank 0 sends
    for n in neighbours:
        # NOTE: Also send to self but who cares
    
        #f.write("Rank %d: posting send to %d\n" % (rank,n) )
        #f.flush()
        
        mpi.MPI_COMM_WORLD.send(content, n, DUMMY_TAG)
        
    #print "rank %i done" %(rank)

else: # others recieve
    message = mpi.MPI_COMM_WORLD.recv(0, DUMMY_TAG)
    assert message == "Message from rank 0"
    #print "rank %i got %s" %(rank,message)
    

#f.write("Done for rank %d\n" % rank)
#f.flush()
#f.close()


# Close the sockets down nicely
mpi.finalize()
