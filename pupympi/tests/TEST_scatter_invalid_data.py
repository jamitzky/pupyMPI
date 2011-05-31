# meta-description: Scatter testing invalid data exceptions
# meta-expectedresult: 0
# meta-minprocesses: 4

from mpi import MPI
from mpi.exceptions import MPIException

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 2


scatter_data = 42 # Is unsliceable!

if rank == SCATTER_ROOT: # Data type errors are only raised for root
    try:
        world.scatter(scatter_data, root=SCATTER_ROOT)
    except MPIException, e:
        assert True
    else:
        # Didn't get expected exception
        assert False
else:
    pass

scatter_data = [42] # Is not sliceable enough!

if rank == SCATTER_ROOT: # Data type errors are only raised for root
    try:
        world.scatter(scatter_data, root=SCATTER_ROOT)
    except MPIException, e:
        assert True
    else:
        # Didn't get expected exception
        assert False
else:
    pass


scatter_data = [42]*(size+1) # Is not finely sliceable

if rank == SCATTER_ROOT: # Data type errors are only raised for root
    try:
        world.scatter(scatter_data, root=SCATTER_ROOT)
    except MPIException, e:
        assert True
    else:
        # Didn't get expected exception
        assert False
else:
    pass


mpi.finalize()
