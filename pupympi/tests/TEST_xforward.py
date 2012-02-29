#!/usr/bin/env python
# meta-description: Test that graphics can be displayed via X forwarding
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-x-forward

import time
import os

from mpi import MPI
from mpi import constants

mpi = MPI()

world = mpi.MPI_COMM_WORLD
rank = world.rank()

# check that we are X forwarding correctly
d = os.getenv('DISPLAY')
assert d is not None

mpi.finalize()
