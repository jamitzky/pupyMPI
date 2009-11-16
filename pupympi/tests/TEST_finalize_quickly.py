#!/usr/bin/env python2.6
# meta-description: The minimal correct pupyMPI program is allowed
# meta-expectedresult: 0
# meta-minprocesses: 1

from mpi import MPI
print "INITTING"
mpi = MPI()
print "\tINITTED"
world = mpi.MPI_COMM_WORLD
rank = world.rank()
#f = open("/tmp/mpi.local.rank%s.log" % rank, "w")

#f.write( "Gonna finalize - rank %d\n" % rank)
#f.flush()
# Close the sockets down nicely

mpi.finalize()

#f.write( "Finalized for rank %d\n" % rank)
#f.flush()

#f.close()

#print "\tCLOSED!"