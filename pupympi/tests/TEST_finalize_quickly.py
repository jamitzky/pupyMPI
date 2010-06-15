#!/usr/bin/env python2.6
# meta-description: The minimal correct pupyMPI program does nothing but finalize
# meta-expectedresult: 0
# meta-minprocesses: 8


from mpi import MPI
from mpi import constants

mpi = MPI()

world = mpi.MPI_COMM_WORLD
rank = world.rank()

f = open(constants.LOGDIR+"mpi.local.finalize.rank%s.log" % rank, "w")

f.write( "Gonna finalize - rank %d\n" % rank)
f.flush()
# Close the sockets down nicely

mpi.finalize()

f.write( "Finalized for rank %d\n" % rank)
f.flush()

f.close()
