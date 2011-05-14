import numpy, sys, time
from mpi import MPI
from mpi.collective.operations import MPI_sum
from mpi.constants import MPI_TAG_ANY

pupy = MPI()
world = pupy.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

def stencil_solver(local,e):
    """
    The function receives a partial system-matrix including ghost rows in top and bottom
    """
    W, H = local.shape
    W -= 2
    H -= 2
    maxrank = size - 1
    
    work = numpy.zeros((W,H)) # temp workspace
    
    cells = local[1:-1, 1:-1] # interior
    left  = local[1:-1, 0:-2]
    up    = local[0:-2, 1:-1]
    down  = local[2:  , 1:-1]    
    right = local[1:-1, 2:  ]

    epsilon = W*H*e
    delta = epsilon+1
    counter = 0
    while epsilon<delta:
        if rank != 0:
            local[:,0] = world.sendrecv(local[:,1], rank-1, MPI_TAG_ANY, rank-1, MPI_TAG_ANY)
        if rank != maxrank:
            local[:,-1] = world.sendrecv(local[:,-2], rank+1, MPI_TAG_ANY, rank+1, MPI_TAG_ANY)
        work[:] = (cells+up+left+right+down)*0.2
        delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)
        cells[:] = work

        counter += 1
        # DEBUG
        #if rank == 0:
        #    print "rank 0 delta:%s" % (delta)
        
    if rank == 0:
        print "rank 0 done, in %i iterations (epsilon:%s)" % (counter, epsilon)
    #print "rank %i done, %s sample:%s" % (rank,e,local[2,0:5])

# for realism one process initializes and distributes the global state
if rank == 0:
    # Fetch command line parameters
    try:
        global_width = int(sys.argv[1])
        global_height = int(sys.argv[2])
        epsilon_factor = float(sys.argv[3])
    except:
        # Not all args we specified
        print "missing or incorrect args (width, height epsilon), going with defaults"
        global_width = 500
        global_height = 500
        epsilon_factor = 0.001
    
    # Ensure that height is a multiple of np
    off = global_height % size 
    if off:
        global_height = global_height - off + size
    
    # Initialize state
    global_state = numpy.zeros(global_width*global_height).reshape(global_height,global_width)
    global_state[[0,-1],:] = 1.0 # fill top and bottom row with 1.0
    global_state[:,[0,-1]] = 0.5 # fill left and right column with 0.5
    #global_state = numpy.random.random(global_width*global_height).reshape(global_height,global_width) # random 0-1.0 in each field
else:
    global_state = []
    epsilon_factor = 0

# All procs receive their local state and add empty ghost rows
epsilon_factor = world.bcast(epsilon_factor, root=0)
local_state = world.scatter(global_state, root=0)
height, width = local_state.shape
empty = numpy.zeros((1,width))
local_state = numpy.concatenate((empty,local_state,empty)) # add ghost rows top and bottom

# DEBUG
#print "rank%i has ls:%s" % (rank,local_state)
if rank == 0:
#    print "rank%i has global state:%s" % (rank,global_state)
    print "Starting to solve for np:%i w:%i h:%i e:%s" % (size, global_width, global_height, epsilon_factor)
    pass

# Do it
t1 = time.time()
stencil_solver(local_state,epsilon_factor)
t = time.time() - t1
if rank == 0:
    print "Solved in %s seconds" % t    

pupy.finalize()