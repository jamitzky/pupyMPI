"""
Network communication - simple
"""

__version__ = 0.01

#from mpi.comm import Communicator


def runner(target, rank, size, *args, **kwargs):
    mpi.MPI_COMM_WORLD = Communicator(rank, size)
    target(*args, **kwargs)

def initialize(size, target, *args, **kwargs):
    # Start np procs and go through with it :)
    from multiprocessing import Process
    procs = {}

    for rank in range(size):
        p = Process(target=runner, args=(target, rank, size) + args, kwargs=kwargs)
        p.start()

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
