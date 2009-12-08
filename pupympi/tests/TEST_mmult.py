#!/usr/bin/env python2.6
# meta-description: Test funky matrix multiplication via allreduce
# meta-expectedresult: 0

from mpi import MPI
    
from mpi.operations import prod

try:
    from numpy import matrix
except ImportError:
    # NOTE: This test relies on Numpy... do we want to fail if not importable?
    mpi = MPI()
    mpi.finalize()
else:
    mpi = MPI()
    
    r = mpi.MPI_COMM_WORLD.rank()+1
    
    local_matrix = matrix( [[r, r, r], [r, r, r], [r, r, r] ])
    
    reduced_matrix = mpi.MPI_COMM_WORLD.allreduce(local_matrix, prod)
    
    if r == 1:
        print reduced_matrix

    mpi.finalize()
