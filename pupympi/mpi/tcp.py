import mpi
import socket
import time

try:
    import cPickle as pickle
except ImportError:
    import pickle

def recv(destination, tag, comm=None):
	return wait(irecv(destination, tag, comm=comm))
	
def irecv(destination, tag, comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD
        
    # Check the destination exists
    if not comm.have_rank(destination):
        raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))
    
    conn, addr = mpi.__server_socket.accept()
    while 1:
        data = conn.recv(1024)
        if not data: break
    print "Vi er kommet hertil ", data, type(data)
    conn.close()
    meaningless_handle_to_be_replaced = pickle.loads(data)
    return meaningless_handle_to_be_replaced

def isend(destination, content, tag, comm=None):
    # Implemented as a regular send until we talk to Brian
    if not comm:
        comm = mpi.MPI_COMM_WORLD

    # Check the destination exists
    if not comm.have_rank(destination):
        raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

    # Find the network details
    dest = comm.get_network_details(destination)
            
    # Rewrite this, when we have the details
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print "socket done... wait a while"
    #time.sleep(2)
    # I think the line below produces a weird error in itself now my mony is on the port numbers being wrong...
    #dummy = raw_input("wait?")
    s.connect((dest['host'], dest['port']))
    time.sleep(2)
    s.send(pickle.dumps(content))
    s.close()
    
    meaningless_handle_to_be_replaced = None
    return meaningless_handle_to_be_replaced

def wait(meaningless_handle_to_be_replaced):
    return meaningless_handle_to_be_replaced
    

def send(destination, content, tag, comm=None):
	return wait(isend(destination, content, tag, comm=comm))
	
def prepare_process(rank):
    # listen to a TCP port so we can receive messages.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind( ('localhost', 6000+rank ))
    s.listen(5)
    mpi.__server_socket = s
