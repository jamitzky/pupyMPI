import socket
from mpi.exceptions import MPIException

def get_socket(min=10000, max=30000):
    """
    A simple helper method for creating a socket,
    binding it to a random free port within the specified range. 
    """
    logger = Logger()
    used = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    
    hostname = socket.gethostname()
    port_no = None

    #logger.debug("get_socket: Starting loop with hostname %s" % hostname)

    while True:
        port_no = random.randint(min, max) 
        if port_no in used:
            logger.debug("get_socket: Port %d is already in use %d" % port_no)
            continue

        try:
            #logger.debug("get_socket: Trying to bind on port %d" % port_no)
            sock.bind( (hostname, port_no) )
            break
        except socket.error, e:
            logger.debug("get_socket: Permission error on port %d" % port_no)
            used.append( port_no ) # Mark socket as used (or no good or whatever)
            raise e
        
    #logger.debug("get_socket: Bound socket on port %d" % port_no)
    return sock, hostname, port_no

class Network(object):
    def __init__(self, options):
        self.options = options
        self.t_in = CommunicationHandler(rank)
        self.t_in.name = "t_in"
        self.t_in.daemon = True
        self.t_in.start()
        
        if options.single_communication_thread:
            self.t_out = self.t_in
        else:
            self.t_out = CommunicationHandler(rank)
            self.t_out.daemon = True
            self.t_out.name = "t_out"
            self.t_out.start()

        self.socket_pool = SocketPool(constants.SOCKET_POOL_SIZE)
        
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.main_receive_socket = socket

    def set_mpi_world(self, MPI_COMM_WORLD):
        self.MPI_COMM_WORLD = MPI_COMM_WORLD

    def handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        #Logger().debug("handshake: Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ),protocol=-1 )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        #Logger().debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        
        # Pack the data with our special format
        header = pack_header(internal_rank, constants.TAG_INITIALIZING, len(data), 0, constants.JOB_INITIALIZING)
        s_conn.send(header + data)
        
        # Receiving data about the communicator, by unpacking the head etc.
        tag, sender, communicator, recv_type, all_procs = structured_read(s_conn)
        #Logger().debug("handshake: Received information for all processes (%d)" % len(all_procs))
        s_conn.close()

        self.all_procs = {}
        for (host, port, global_rank) in all_procs:
            self.all_procs[global_rank] = {'host' : host, 'port' : port, 'global_rank' : global_rank}

    def start_collective(self, request, communicator, jobtype, data, callbacks=[]):
        Logger().info("Starting a %s collective network job with %d callbacks" % (type, len(callbacks)))
        
        job = {'type' : jobtype, 'data' : data, 'request' : request, 'status' : 'new', 'callbacks' : callbacks, 'communicator' : communicator, 'persistent': True}
        tree = BroadCastTree(range(communicator.size()), communicator.rank())
        tree.up()
        tree.down()


    def finalize(self):
        """
        Forwarding the finalize call to the threads. Look at the 
        CommunicationHandler.finalize for a deeper description of
        the shutdown procedure. 
        """
        self.t_in.finalize()
        if not self.options.single_communication_thread:
            self.t_out.finalize()
        self.main_receive_socket.close()

class CommunicationHandler(object):
    """
    """
    # Add two TCP specific lists. Read and write sockets
    self.sockets_in = []
    self.sockets_out = []



class SocketPool(object):
    """
    This class manages a pool of socket connections. You request and delete
    connections through this class.
    
    The class has room for a number of cached socket connections, so if your
    connection is heavily used it will probably not be removed. This way your
    call will not create and teardown the connection all the time. 
    
    NOTE: The number of cached elements are controlled through the constants 
    module, even though it might be exposed at a later point through command
    line arguments for mpirun.py
    
    NOTE 2: It's possible to mark a connections as mandatory persistent. This
    will not always give you nice performance. Please don't use this feature
    too much as it will push other connections out of the cache. And these
    connections might be more important than your custom one.
    
    IMPLEMENTATION: This is a modified "Second change FIFO cache replacement
    policy" algorithm. It's modified by allowing some elements to live 
    forever in the cache.
    
    ERRORS: It's possible to trigger an error if you fill up the cache with
    more persistent connections than the buffer can actually contain. An
    MPIException will be raised in this situation. 
    """
    
    def __init__(self, max_size):
        self.sockets = []
        self.max_size = max_size
        self.metainfo = {}
        
    def get_socket(self, rank, socket_host, socket_port, force_persistent=False):
        """
        Returns a socket to the specific rank. Consider this function 
        a black box that will cache your connections when it is 
        possible.
        """
        client_socket = self._get_socket_for_rank(rank) # Try to find an existing socket connection
        newly_created = False
        if not client_socket: # If we didn't find one, create one
            receiver = (socket_host, socket_port)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( receiver )
            
            if len(self.sockets) > self.max_size: # Throw one out if there are too many
                self._remove_element()
                
            # Add the new socket to the list
            self._add(rank, client_socket, force_persistent)
            newly_created = True
            
        return client_socket, newly_created

    def _remove_element(self):
        """
        Finds the first element that already had it's second chance and
        remove it from the list.
        
        NOTE: Shouldn't we close the socket we are removing here?
        NOTE-ANSWER: Yes.. maybe.. but that will not improve correctness
        """
        for x in range(2): # Run through twice
            for socket in self.sockets:
                (srank, sreference, force_persistent) = self.metainfo[socket]
                if force_persistent: # We do not remove persistent connections
                    continue
                
                if sreference: # Mark second chance
                    self.metainfo[socket] = (srank, False, force_persistent)
                else: # Has already had its second chance
                    self.sockets.remove(socket) # remove from socket pool
                    del self.metainfo[socket] # delete metainfo
                    break

        raise MPIException("Not possible to add a socket connection to the internal caching system. There are %d persistant connections and they fill out the cache" % self.max_size)
    
    def _get_socket_for_rank(self, rank):
        """
        Attempts to find an already created socket with a connection to a
        specific rank. If this does not exist we return None
        """
        for socket in self.sockets:
            (srank, _, fp) = self.metainfo[socket]
            if srank == rank:
                self.metainfo[socket] = (srank, True, fp)
                return socket
        
        return None
    
    def _add(self, rank, socket, force_persistent):
        self.metainfo[socket] = (rank, True, force_persistent)
        self.sockets.append(socket)
    
