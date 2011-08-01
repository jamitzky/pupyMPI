import numpy, sys, time
from mpi import MPI
from mpi.collective.operations import MPI_sum

pupy = MPI()
world, rank, size = pupy.initinfo

def stencil_solver(local,epsilon):
    """
    The function receives a partial system-matrix including ghost rows in top and bottom
    """

    # We define the data size as the product of W and H times the byte size of the inner
    # data type.
    W, H = local.shape
    maxrank = size - 1

    work = numpy.zeros((W-2,H-2)) # temp workspace

    cells = local[1:-1, 1:-1] # interior
    left  = local[1:-1, 0:-2]
    up    = local[0:-2, 1:-1]
    down  = local[2:  , 1:-1]
    right = local[1:-1, 2:  ]

    delta = epsilon+1
    counter = 0
    while epsilon<delta:
        if rank != 0:
            local[0,:] = world.sendrecv(local[1,:], dest=rank-1)
        if rank != maxrank:
            local[-1,:] = world.sendrecv(local[-2,:], dest=rank+1)
        work[:] = (cells+up+left+right+down)*0.2

        delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)

        cells[:] = work
        counter += 1

    if rank == 0:
        print "rank %i done, in %i iterations with final delta:%s (sample:%s)" % (rank, counter, delta, cells[10,34:42])

# for realism one process initializes and distributes the global state
global_width = 500
global_height = 500
epsilon_factor = 10000.0

if rank == 0:
    # Fetch command line parameters
    try:
        global_width = int(sys.argv[1])
        global_height = int(sys.argv[2])
        epsilon_factor = float(sys.argv[3])
    except Exception, e:
        print e
        print "missing or incorrect args (width, height epsilon), going with defaults"

    epsilon = global_width*global_height/epsilon_factor # compute stoping threshold
    # Ensure that height is a multiple of np
    off = global_height % size
    if off:
        global_height = global_height - off + size

    # Initialize state
    global_state = numpy.zeros(global_width*global_height).reshape(global_height,global_width)
    global_state[[0,-1],:] = 1.0 # fill top and bottom row with 1.0
    global_state[:,[0,-1]] = 0.5 # fill left and right column with 0.5
else:
    global_state = []
    epsilon = 0

if rank == 0:
    datasize = global_height*global_width*global_state.dtype.itemsize
else:
    datasize = -1

# All procs receive their local state and add empty ghost rows
epsilon = world.bcast(epsilon, root=0)
local_state = world.scatter(global_state, root=0)
height, width = local_state.shape
empty = numpy.zeros((1,width))
local_state = numpy.concatenate((empty,local_state,empty)) # add ghost rows top and bottom

if rank == 0:
    print "Starting to solve for np:%i w:%i h:%i e:%s" % (size, global_width, global_height, epsilon)

stencil_solver(local_state,epsilon)


pupy.finalize()
