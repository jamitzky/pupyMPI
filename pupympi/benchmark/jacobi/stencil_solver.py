import numpy, sys, time
from mpi import MPI
from mpi.collective.operations import MPI_sum

pupy = MPI()
world, rank, size = pupy.initinfo

def stencil_solver(local,epsilon):
    """
    The function receives a partial system-matrix including ghost rows in top and bottom
    """
    from mpi.benchmark import Benchmark

    # We define the data size as the product of W and H times the byte size of the inner
    # data type.
    datasize = height*width*local.dtype.itemsize
    bw = Benchmark(world, datasize=datasize)

    # We wish to benchmark the complete solving (identifier complete), the edge exchange
    # identifier (edge) and the delta calculation (identifier delta).
    bw_complete, _ = bw.get_tester("complete")
    bw_edge, _ = bw.get_tester("edge")
    bw_delta, _ = bw.get_tester("delta")

    bw_complete.start()

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
        bw_edge.start()
        if rank != 0:
            local[0,:] = world.sendrecv(local[1,:], dest=rank-1)
        if rank != maxrank:
            local[-1,:] = world.sendrecv(local[-2,:], dest=rank+1)
        bw_edge.stop()
        work[:] = (cells+up+left+right+down)*0.2

        bw_delta.start()
        delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)
        bw_delta.stop()

        cells[:] = work
        counter += 1

    if rank == 0:
        print "rank %i done, in %i iterations with final delta:%s (sample:%s)" % (rank, counter, delta, cells[10,34:42])

    bw_complete.stop()

    # Flush the benchmarked data to files
    bw.flush()


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
        epsilon_factor = 10000.0

    epsilon = global_width*global_height/epsilon_factor # compute stoping threshold
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
    epsilon = 0

# All procs receive their local state and add empty ghost rows
epsilon = world.bcast(epsilon, root=0)
local_state = world.scatter(global_state, root=0)
height, width = local_state.shape
empty = numpy.zeros((1,width))
local_state = numpy.concatenate((empty,local_state,empty)) # add ghost rows top and bottom

# DEBUG
#print "rank%i has ls:%s" % (rank,local_state)
if rank == 0:
#    print "rank%i has global state:%s" % (rank,global_state)
    print "Starting to solve for np:%i w:%i h:%i e:%s" % (size, global_width, global_height, epsilon)
    pass

# Do it
t1 = time.time()
stencil_solver(local_state,epsilon)
t = time.time() - t1
if rank == 0:
    print "Solved in %s seconds" % t

pupy.finalize()
