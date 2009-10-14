import socket
from mpi.exceptions import MPIException
from mpi.network.utils import get_socket
from mpi.network.socketpool import SocketPool

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

