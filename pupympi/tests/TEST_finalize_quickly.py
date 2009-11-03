#!/usr/bin/env python2.6
# meta-description: The minimal correct pupyMPI program is allowed
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI

# Close the sockets down nicely
mpi.finalize()

