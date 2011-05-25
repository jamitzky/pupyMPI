# meta-description: Test scatter with different types
# meta-expectedresult: 0
# meta-minprocesses: 4
import numpy

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

#SCATTER_ROOT = 2
# DEBUG
SCATTER_ROOT = 0

## List
#if rank == SCATTER_ROOT:
#    scatter_data = [[x]*2 for x in range(size)]
#else:
#    scatter_data = None
#
#my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
#assert my_data == [[rank,rank]]
#
# Numpy array
chunksize = 5
if rank == SCATTER_ROOT:    
    scatter_data = numpy.arange(size*chunksize)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert numpy.alltrue(my_data == numpy.arange(rank*chunksize,(rank+1)*chunksize))

## 4D Numpy float array
#if rank == SCATTER_ROOT:    
#    scatter_data = numpy.arange(size*chunksize*12).reshape(size*3,chunksize,2,2)
#else:
#    scatter_data = None
#
#my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
##print "rank:%i got:%s shape:%s" % (rank, my_data, my_data.shape)
#assert numpy.alltrue(my_data == numpy.arange(rank*chunksize*12,(rank+1)*chunksize*12).reshape(3,5,2,2) )

mpi.finalize()

