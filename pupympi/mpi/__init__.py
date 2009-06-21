__version__ = 0.01

from mpi.comm import Communicator
import mpi
import socket

# Define exceptions
class MPIBadAddressException(Exception): pass

def runner(target, rank, size, process_placeholder, *args, **kwargs):
    mpi.MPI_COMM_WORLD = Communicator(rank, size, process_placeholder)

    # listen to a TCP port so we can receive messages.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind( ('localhost', 6000+rank ))
    s.listen(5)

    mpi.__server_socket = s

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
        allprocesses.append( (rank, p, {'port' : 6000 + rank, 'host' : ''}) )   

    for rank in process_list:
        placeholder = process_list[rank]['all']
        placeholder['self'] = process_list[rank]['process']
        placeholder['all'] = allprocesses

    [ p.start() for (_,p, _) in allprocesses ]

def finalize():
    #mpi.__server_socket.shutdown(socket.SHUT_RDWR) # Disallow both receives and sends
    pass

def rank(comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD
    return comm.rank

def size(comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD
    return comm.size

from mpi.tcp import isend, irecv

__all__ = ('initialize', 'finalize', 'rank', 'size', 'isend', 'irecv', )
