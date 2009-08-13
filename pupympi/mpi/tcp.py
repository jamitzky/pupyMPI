import mpi, time, socket
from mpi.logger import Logger
import threading

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class TCPNetwork():
    def __init__(self, start_port_no=None):
        self.hostname = socket.gethostname()
        self.bind_socket()
    
        if start_port_no:
            self.start_port_no = start_port_no

    def bind_socket(self):
        start_port = getattr(self, 'start_port_no', 14000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger = Logger()

        logger.debug("Starting on port_no %d" % start_port)

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
    def run(self, start_port_no=None):
        self.alive = True
        self.hostname = socket.gethostname()
        self.bind_socket()
    
        if start_port_no:
            self.start_port_no = start_port_no
            
        while self.alive:
            time.sleep(2)
            print "yawn"

    def bind_socket(self):
        start_port = getattr(self, 'start_port_no', 14000)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger = Logger()

        logger.debug("Starting on port_no %d" % start_port)

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
        self.alive = False
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
    