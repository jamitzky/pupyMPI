#!/usr/bin/env python2.6
# meta-description: Testing the sendrecv call. Runs with odd no. of processes who pass a token around
# meta-expectedresult: 0
# meta-minprocesses: 5
# meta-max_runtime: 90


from mpi import MPI
from mpi import constants

import time

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


#assert size % 2 == 1 # Require odd number of participants

content = "conch"
DUMMY_TAG = 1

# Log stuff so progress is easier followed
f = open(constants.LOGDIR+"mpi.sendreceive.rank%s.log" % rank, "w")


# Send up in chain, recv from lower (with usual wrap around)
dest   = (rank + 1) % size
source = (rank - 1) % size

recvdata = mpi.MPI_COMM_WORLD.sendrecv(content+" from "+str(rank), dest, DUMMY_TAG, source, DUMMY_TAG)
f.write("Rank %s passing on %s \n" % (rank, recvdata) )
f.flush()


f.write("Done for rank %d\n" % rank)
f.flush()
f.close()

# Close the sockets down nicely
mpi.finalize()
