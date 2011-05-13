
import numpy

from mpi import MPI
from mpi.collective.operations import MPI_sum

pupy = MPI()
world = pupy.MPI_COMM_WORLD


rank = world.rank()
size = world.size()
maxrank = size - 1

TAG = 42 # just a dummy

    
"""
cells = na0[1:-1, 1:-1] # interior
up    = na0[1:-1, 0:-2] # I think this is left but orientation does not matter...
left  = na0[0:-2, 1:-1] # I think this is up
right = na0[2:  , 1:-1]    
down  = na0[1:-1, 2:  ]
"""
    

def stencil_solver(local):
    """
    The function receives a partial system-matrix
    including ghost rows in top and bottom
    """
    W, H = local.shape
    W -= 2
    H -= 2
    
    work = numpy.zeros((W,H))
    
    cells = local[1:-1, 1:-1] # interior
    up    = local[1:-1, 0:-2] # I think this is left but orientation does not matter...
    left  = local[0:-2, 1:-1] # I think this is up
    right = local[2:  , 1:-1]    
    down  = local[1:-1, 2:  ]

    epsilon = W*H*0.01
    delta = epsilon+1
    i=0
    while epsilon<delta:
        # exchange up (actually left)
        if rank != 0:
            local[:,0] = world.sendrecv(local[:,1], rank-1, TAG, rank-1, TAG)
        # exchange down (actually right)
        if rank != maxrank:
            local[:,-1] = world.sendrecv(local[:,-2], rank+1, TAG, rank+1, TAG)
        work[:] = (cells+up+left+right+down)*0.2
        delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)
        cells[:] = work
        # DEBUG
        #if rank == 0:
        #    print "rank 0 delta:%s" % (delta)
        
    #if rank == 0:
    #    print "rank 0 done, cells:",cells

# for realism proc 0 initializes and distributes the global state
if rank == 0:
    # Initialize state
    problem_scale = 4 # how many rows for each process
    global_width = 6
    global_height = problem_scale * world.size()
    global_state = numpy.random.random(global_width*global_height).reshape(global_height,global_width)
    # DEBUG
    #global_state = numpy.arange(global_width*global_height).reshape(global_height,global_width)
else:
    global_state = []

# All procs receive their local state and add empty ghost rows
local_state = world.scatter(global_state, root=0)
height, width = local_state.shape
empty = numpy.zeros((1,width))
local_state = numpy.concatenate((empty,local_state,empty)) # add ghost rows top and bottom

# DEBUG
#if rank == 0:
#    print "rank%i has global state:%s" % (rank,global_state)
#print "rank%i has ls:%s" % (rank,local_state)

# Do it
stencil_solver(local_state)

pupy.finalize()