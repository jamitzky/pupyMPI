#!/usr/bin/env python2.6
# meta-description: Testing the sendrecv call. Runs with odd no. of processes who pass a token around
# meta-expectedresult: 0
# meta-minprocesses: 5
# meta-max_runtime: 90

# This test is meant to be run with a odd number of processes
# With debugging on 13 procs can throw around the token in just under a minute, so if 5 can't do it in 1.5 minutes something is wrong
"""
as of 22/11-09 this test has serious problems with more than 9 procs. Often the
first run is fine but even with a few seconds to cool of the next runs often hang

- seems like sometimes a proccess recieves the token, but has not recieved all
the start up messages from lower ranking processes. Therefore it has not left
initialization and so does not pass on the token to the neighbour.
Can it be that some of the lower ranks can actually manage to start up, recieve
from lower, send off to all uppers and the recieve and pass on the token AND then
shutdown sleeping for 4 secs and die and break socket before a higher gets the
startup message?

Sleep(9) does help a lot ... :/

If we had a barrier we could test it
"""

from mpi import MPI
import time

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


assert size % 2 == 1 # Require odd number of participants

content = "conch"
DUMMY_TAG = 1

# Log stuff so progress is easier followed
f = open("/tmp/mpi.sendrecv.rank%s.log" % rank, "w")


# Send up in chain, recv from lower (with usual wrap around)
dest   = (rank + 1) % size
source = (rank - 1) % size

recvdata = mpi.MPI_COMM_WORLD.sendrecv(content+" from "+str(rank), dest, DUMMY_TAG, source, DUMMY_TAG)
f.write("Rank %s passing on %s \n" % (rank, recvdata) )
f.flush()


f.write("Done for rank %d\n" % rank)
f.flush()
f.close()

# Three seperate sleeps for superstition
time.sleep(3)
time.sleep(3)
time.sleep(3)

# Close the sockets down nicely
mpi.finalize()
