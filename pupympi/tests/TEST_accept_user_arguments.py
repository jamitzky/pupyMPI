#!/usr/bin/env python2.6
# meta-description: Tests that we can accept user arguments. 
# meta-expectedresult: 0
# meta-minprocesses: 1
# meta-userargs: arg0 arg1 -o -p -xys --long-argument
from mpi import MPI

mpi = MPI()

import sys
print sys.argv

# We don't consider the first argument as this will be this script
# it's hard for us to take into account the paths and other stuff
received_args = " ".join(sys.argv[1:])
assert received_args == "arg0 arg1 -o -p -xys --long-argument"

mpi.finalize()
