import mpi, time, socket, threading, random
from mpi.logger import Logger

try:
    import cPickle as pickle
except ImportError:
    import pickle

def get_socket(range=(10000, 30000)):
    """
    A simple helper method for creating a socket,
    binding it to a fee port. 
    """
    logger = Logger()
    used = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    
    hostname = socket.gethostname()
    port_no = None

    logger.debug("get_socket: Starting loop with hostname %s" % hostname)

    while True:
        port_no = int(random.uniform(*range))
        if port_no in used:
            logger.debug("get_socket: Port %d is already in use %d" % port_no)
            continue

        try:
            logger.debug("get_socket: Trying to bind on port %d" % port_no)
            sock.bind( (hostname, port_no) )
            break
        except socket.error, e:
            raise e
            logger.debug("get_socket: Permission error on port %d" % port_no)
            used.append( port_no )

    logger.debug("get_socket: Bound socket on port %d" % port_no)
    return sock, hostname, port_no
    
class TCPNetwork:

    def __init__(self):
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.socket = socket

        logger = Logger().debug("Network started on port %s" % port_no)

    def handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        logger = Logger()

        logger.debug("Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ) )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        logger.debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        s_conn.send(data)
        
        # Receiving data about the communicator
        all_procs = s_conn.recv(1024)
        all_procs = pickle.loads( all_procs )
        logger.debug("Received information for all processes (%d)" % len(all_procs))
        s_conn.close()
        
        logger.debug("Shaking done")
        
        return all_procs

    def finalize(self):
        self.socket.close()
        logger = Logger().debug("The TCP network is closed")

    def recv(self, destination, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination):
            error_str = "No process with rank %d in communicator %s. " % (destination, comm.name)
            raise MPIBadAddressException(error_str)
        
        # Get incoming communication
        conn, addr = self.socket.accept()
        msg = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            else:
                msg += data
            
        conn.close()
        unpickled_data = pickle.loads(msg)
        return unpickled_data
        
    def irecv(self, destination, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination):
            error_str = "No process with rank %d in communicator %s. " % (destination, comm.name)
            raise MPIBadAddressException(error_str)
        
        # Get incoming communication
        conn, addr = self.socket.accept()
        msg = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            else:
                msg += data
            
        conn.close()
        unpickled_data = pickle.loads(msg)
        return unpickled_data

    def isend(self, destination_rank, content, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination_rank):
            raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

        # Find the network details for recieving rank
        host,port = comm.get_network_details(destination_rank)
            
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        s.setblocking(False) # False flag means non blocking
        s.connect((host, port))
        s.send(pickle.dumps("y"))
        #s.send(pickle.dumps(content))
        
        s.close()
        
        meaningless_handle_to_be_replaced_could_be_a_status_code = None
        return meaningless_handle_to_be_replaced_could_be_a_status_code

    def wait(self, meaningless_handle_to_be_replaced):
        return meaningless_handle_to_be_replaced
    
    def barrier(self, comm):
        # TODO Implement
        pass
        
    def send(self, destination_rank, content, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination_rank):
            raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

        # Find the network details for recieving rank
        host,port = comm.get_network_details(destination_rank)
                
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.send(pickle.dumps(content))
        s.close()
        
        meaningless_handle_to_be_replaced_could_be_a_status_code = None
        return meaningless_handle_to_be_replaced_could_be_a_status_code
    
class ThreadTCPNetwork(threading.Thread):
    #def __init__(self):
    #    self.hostname = socket.gethostname()
    #    self.bind_socket()
    
    def run(self):
        logger.debug("starting run method")
        self.hostname = socket.gethostname()
        logger.debug("got host name")
        self.bind_socket()
        logger.debug("finishing run method")
        self.alive = True
        while self.alive:
            time.sleep(2)
            logger.debug("HEARTBEAT")
            pass

    def set_start_port(self, port_no):
        self.start_port_no = port_no
        
    def bind_socket(self):
        start_port = getattr(self, 'start_port_no', 14000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        for tries in range(10):
            try:
                s.bind( (self.hostname, start_port+tries))
                self.port = start_port+tries
                break
            except socket.error:
                continue

        s.listen(5)
        self.socket = s
        
    def handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        logger = Logger()

        logger.debug("Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ) )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        logger.debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        s_conn.send(data)
        
        # Receiving data about the communicator
        all_procs = s_conn.recv(1024)
        all_procs = pickle.loads( all_procs )
        logger.debug("Received information for all processes (%d)" % len(all_procs))
        s_conn.close()
        
        logger.debug("Shaking done")
        
        return all_procs

    def finalize(self):
        self.socket.close()
        logger = Logger()
        logger.debug("The TCP network is closed")

    def recv(self, destination, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination):
            error_str = "No process with rank %d in communicator %s. " % (destination, comm.name)
            raise MPIBadAddressException(error_str)
        
        # Get incoming communication
        conn, addr = self.socket.accept()
        msg = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            else:
                msg += data
            
        conn.close()
        unpickled_data = pickle.loads(msg)
        return unpickled_data
        
    def irecv(self, destination, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination):
            error_str = "No process with rank %d in communicator %s. " % (destination, comm.name)
            raise MPIBadAddressException(error_str)
        
        # Get incoming communication
        conn, addr = self.socket.accept()
        msg = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break
            else:
                msg += data
            
        conn.close()
        unpickled_data = pickle.loads(msg)
        return unpickled_data

    def isend(self, destination_rank, content, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination_rank):
            raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

        # Find the network details for recieving rank
        host,port = comm.get_network_details(destination_rank)
            
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        s.setblocking(False) # False flag means non blocking
        s.connect((host, port))
        s.send(pickle.dumps("y"))
        #s.send(pickle.dumps(content))
        
        s.close()
        
        meaningless_handle_to_be_replaced_could_be_a_status_code = None
        return meaningless_handle_to_be_replaced_could_be_a_status_code

    def wait(self, meaningless_handle_to_be_replaced):
        return meaningless_handle_to_be_replaced
        
    def send(self, destination_rank, content, tag, comm):
        # Check the destination exists
        if not comm.have_rank(destination_rank):
            raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

        # Find the network details for recieving rank
        host,port = comm.get_network_details(destination_rank)
                
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.send(pickle.dumps(content))
        s.close()
        
        meaningless_handle_to_be_replaced_could_be_a_status_code = None
        return meaningless_handle_to_be_replaced_could_be_a_status_code
