__version__ = 0.01

from mpi.comm import Communicator
import mpi

def runner(target, rank, size, process_placeholder, *args, **kwargs):
    mpi.MPI_COMM_WORLD = Communicator(rank, size, process_placeholder)
    target(*args, **kwargs)

def initialize(size, target, *args, **kwargs):
    # Start np procs and go through with it :)
    from multiprocessing import Process

    process_list = {}
    allprocesses = []

    for rank in range(size):
        process_placeholder = {}
        p = Process(target=runner, args=(target, rank, size, process_placeholder) + args, kwargs=kwargs)
        process_list[ rank ] = {'process' : p, 'all' : process_placeholder }
        allprocesses.append( (rank, p) )   

    for rank in process_list:
        placeholder = process_list[rank]['all']
        placeholder['self'] = process_list[rank]['process']
        placeholder['all'] = allprocesses

    [ p.start() for (_,p) in allprocesses ]

def rank(comm=None):
    import mpi
    if not comm:
        comm = mpi.MPI_COMM_WORLD
    return comm.rank

def size(comm=None):
    import mpi
    if not comm:
        comm = mpi.MPI_COMM_WORLD
    return comm.size
