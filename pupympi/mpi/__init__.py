__version__ = 0.01

from mpi.comm import Communicator
from mpi.simplecomm.simplecomm import Testy
#import mpi.simplecomm
import mpi


NETWORK_METHOD = "tcp"
if NETWORK_METHOD == "tcp":
    from mpi.tcp import isend, irecv, prepare_process, wait, send, recv
    
    
# Define exceptions
class MPIBadAddressException(Exception): pass

def runner(target, rank, size, process_placeholder, *args, **kwargs):
    mpi.MPI_COMM_WORLD = Communicator(rank, size, process_placeholder)
    prepare_process( rank )
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
        allprocesses.append( (rank, p, {'port' : 6000 + rank, 'host' : '127.0.0.1'}) )   

    for rank in process_list:
        placeholder = process_list[rank]['all']
        placeholder['self'] = process_list[rank]['process']
        placeholder['all'] = allprocesses

    [ p.start() for (_,p, _) in allprocesses ]

def finalize():
    # Do stuff with this call (move it to tcp if we need it)
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

__all__ = ('initialize', 'finalize', 'rank', 'size', 'isend', 'irecv', 'wait', 'recv', 'send' )
