import mpi, time, socket

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
class TCPNetwork():
    def __init__(self):
        self.hostname = socket.gethostname()
        self.bind_socket()

    def set_logger(self, logger):
        self.logger = logger

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
        self.logger.debug("Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ) )
        
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

    def recv(self, destination, tag, comm=None):
        return self.wait(self.irecv(destination, tag, comm=comm))
        
    def irecv(self, destination, tag, comm=None):
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

    def isend(self, destination, content, tag, comm=None):
        # Implemented as a regular send until we talk to Brian
        print destination
        print "comm:" 
        print comm
        if not comm:
            comm = mpi.MPI_COMM_WORLD

        # Check the destination exists
        if not comm.have_rank(destination):
            raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))

        # Find the network details
        dest = comm.get_network_details(destination)
                
        # Rewrite this, when we have the details
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #time.sleep(2)
        # I think the line below produces a weird error in itself now my mony is on the port numbers being wrong...
        #dummy = raw_input("wait?")
        s.connect((dest['host'], dest['port']))
        time.sleep(2)
        s.send(pickle.dumps(content))
        s.close()
        
        meaningless_handle_to_be_replaced = None
        return meaningless_handle_to_be_replaced

    def wait(self, meaningless_handle_to_be_replaced):
        return meaningless_handle_to_be_replaced
        
    def send(destination, content, tag, comm=None):
        return self.wait(self.isend(destination, content, tag, comm=comm))
	
