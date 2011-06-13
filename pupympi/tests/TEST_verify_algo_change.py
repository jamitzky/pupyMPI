# meta-description: Scatter test with various data sizes
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
import numpy

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 0
if rank == SCATTER_ROOT:
    scatter_data = numpy.arange(size)
else:
    scatter_data = None

req = world.iscatter(scatter_data, root=SCATTER_ROOT)

my_data = req.wait()
assert my_data == [rank]

# The root is the only node with knowledge of the data so it will be the only once
# that can actually make the request type right. We ensure that the root request
# haven't got an inner request.
if rank == SCATTER_ROOT:
    assert req.is_dirty() == True
    assert req._overtaken_request == None
else:
    # If we are not the root we have been overtaken for sure. We should still be
    # marked as dirty though.
    assert req.is_dirty() == True
    assert req._overtaken_request != None
    
    # Verify proper method transfer
    r1 = req
    r2 = req._overtaken_request
    
    assert r1.acquire == r2.acquire
    assert r1.release == r2.release
    assert r1.test == r2.test
    assert r1.wait == r2.wait
    assert r1.accept_msg == r2.accept_msg
    assert r1.is_dirty == r2.is_dirty
    assert r1.mark_dirty == r2.mark_dirty

mpi.finalize()

