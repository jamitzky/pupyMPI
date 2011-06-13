# meta-description: Test scatter with different types
# meta-expectedresult: 0
# meta-minprocesses: 4
import numpy

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 4
# DEBUG
#SCATTER_ROOT = 0

# List
if rank == SCATTER_ROOT:
    scatter_data = [[x]*2 for x in range(size)]
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert my_data == [[rank,rank]]

# bytearray
chunksize = 4
import string
# set it up so rank 0 gets 'a'*chunksize rank 1 gets 'b'*chunksize and so on
basebytes = bytearray( ''.join([l*chunksize for l in string.ascii_letters[:size]]) )

if rank == SCATTER_ROOT:    
    scatter_data = basebytes
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert numpy.alltrue(my_data == bytearray( string.ascii_letters[rank]*chunksize ) )

# Numpy array
chunksize = 5
if rank == SCATTER_ROOT:    
    scatter_data = numpy.arange(size*chunksize)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert numpy.alltrue(my_data == numpy.arange(rank*chunksize,(rank+1)*chunksize))
#print "rank %i got %s" % (rank, my_data)


# multidimensional Numpy float arrays
chunksize = 3
if rank == SCATTER_ROOT:
    #2*3*2 ints of 8 bytes = 96 bytes = 48 bytes per proc
    scatter_data = numpy.arange(size*chunksize*2*5).reshape(size*2,chunksize,5)
else:
    scatter_data = None
my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert numpy.alltrue(my_data == numpy.arange(rank*chunksize*2*5,(rank+1)*chunksize*2*5).reshape(2,chunksize,5) )

# 4D Numpy float array
if rank == SCATTER_ROOT:    
    scatter_data = numpy.arange(size*chunksize*12).reshape(size*3,chunksize,2,2)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
assert numpy.alltrue(my_data == numpy.arange(rank*chunksize*12,(rank+1)*chunksize*12).reshape(3,chunksize,2,2) )

mpi.finalize()

