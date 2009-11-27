from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Make every processes send their rank to the root. 

ROOT = 3

received = world.gather(rank+1, root=ROOT)

if ROOT == rank:
    assert received == range(1, size+1)
else:
    assert received == None
    
mpi.finalize()