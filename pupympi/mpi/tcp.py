import mpi, time, socket

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class TCPNetwork():
    def __init__(self, mpi_instance):
        self.logger = mpi_instance.logger
        self.mpi_instance = mpi_instance
        self.hostname = socket.gethostname()
        self.port = 14000+mpi_instance.rank()#FIXME: This should just locate a free port.
        
        self.bind_socket()
        
    def bind_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind( (self.hostname, self.port ))
        s.listen(5)
        self.socket = s
        
    def handshake(self, mpirun_hostname, mpirun_port):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        self.logger.debug("Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, self.mpi_instance.rank() ) )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        self.logger.debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        s_conn.send(data)
        
        # Receiving data about the communicator
        all_procs = s_conn.recv(1024)
        all_procs = pickle.loads( all_procs )
        self.logger.debug("Received information for all processes (%d)" % len(all_procs))
        s_conn.close()
        
        self.logger.debug("Shaking done")
        
        return all_procs

    def finalize(self):
        self.socket.close()
        self.logger.debug("The TCP network is closed")

def recv(destination, tag, comm=None):
	return wait(irecv(destination, tag, comm=comm))
	
def irecv(destination, tag, comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD
        
    # Check the destination exists
    if not comm.have_rank(destination):
        error_str = "No process with rank %d in communicator %s. " % (destination, comm.name)
        raise MPIBadAddressException(error_str)
    
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
	