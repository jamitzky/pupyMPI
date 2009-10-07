import mpi, time, socket, threading, random, select, struct
from mpi.logger import Logger
from mpi.network import AbstractNetwork, AbstractCommunicationHandler
from threading import Thread, activeCount
from mpi.bc_tree import BroadCastTree
from mpi import constants

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
def get_header_format():
    format = "lllll"
    size = struct.calcsize(format) 
    return (format, size )
    
def unpack_header(data):
    format, header_size = get_header_format()
    return struct.unpack(format, data[:header_size])
    
def pack_header(*args):
    format, _ = get_header_format()
    return struct.pack(format, *args)

def structured_read(socket_connection):
    """
    Read an entire message from a socket connection
    and return the tag, sender rank and message. 
    
    The stucture of all MPI messages consists
    of a fixed size header and a variable length message.
    
    The header has these fields:
        sender       : integer
        tag          : integer
        msg_size     : integer
        communicator : integer
        type         : integer

    The method is constructed around two recieve loops. In the first loop
    contents of the header is recieved and then unpacked. In the second loop
    The msg_size from the header is used to receive the rest of the message. 
    """
    _, header_size = get_header_format()
    header_unpacked = False

    # The end variables to return
    tag = sender = None
    data = ''

    # get the header
    while not header_unpacked:
        data += socket_connection.recv(header_size)
        
        if len(data) >= header_size:
            sender, tag, msg_size, communicator, recv_type = unpack_header(data)
            Logger().info("Data from header unpack is sender(%s) tag(%s) msg_size(%s) communicator(%s) and recv_type(%s)" % (sender, tag, msg_size, communicator, recv_type))
            header_unpacked = True
    
    # receive the rest of the data 
    total_msg_size = msg_size + header_size
    recv_size = msg_size

    Logger().debug("Starting receive second loop with total_msg_size(%d) and recv_size(%d)" %(total_msg_size, recv_size))

    while len(data) < total_msg_size:
        recv_size = total_msg_size - len(data)
        data += socket_connection.recv(recv_size)
    
    # unpacking the data
    data = pickle.loads(data[header_size:])

    return tag, sender, communicator, recv_type, data

def get_socket(min=10000, max=30000):
    """
    A simple helper method for creating a socket,
    binding it to a random free port within the specified range. 
    """
    logger = Logger()
    used = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    hostname = socket.gethostname()
    port_no = None

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
        
    return sock, hostname, port_no

class TCPCommunicationHandler(AbstractCommunicationHandler):
    """
    This is the TCP implementation of the main CommunicationHandler. There
    will be one or two threads of this class.

    The main purpose of this class is to select on a read and writelist and
    and handle incoming / outgoing requests. 

    Whenever some job is completed the request object matching the job will
    be updated. 

    We also keep an internal queue of the jobs not mathing a request object 
    yet. Whenever a new request object comes into the queue we look through
    the already finished TCP jobs to find a matching one. In this case a recv()
    call might return almost without blocking.

    FIXME: Document the job structure. We need a clear overview of the fields,
           their behaviour etc. Do this somewhere nice so it ends up in the
           documentation. 

    FIXME: Look at persistent socket behaviour. 
    """

    def __init__(self, *args, **kwargs):
        super(TCPCommunicationHandler, self).__init__(*args, **kwargs)

        # Add two TCP specific lists. Read and write sockets
        self.sockets_in = []
        self.sockets_out = []
        self.socket_to_job = {}

    def add_out_job(self, job):
        super(TCPCommunicationHandler, self).add_out_job(job)
        Logger().debug("Adding outgoing job")

        # This is a sending operation. We create a socket 
        # for the job, so we can select from it later. 
        receiver = ( job['participant']['host'], job['participant']['port'],)
        if not job['socket']:
            # Create a client socket and connect to the other end
            client_socket, created = self.socket_pool.get_socket(job['global_rank'], job['participant']['host'], job['participant']['port'])
            if created:
                self.sockets_out.append(client_socket)

                # The other side will probably write on this. FIXME: Make sure we have
                # a method on the pool for adding an already created connection. 
                self.sockets_in.append( client_socket)
            job['socket'] = client_socket 
        job['status'] = 'ready'

        # Tag the socket with a job so we can find it again
        if not job['socket'] in self.socket_to_job:
            self.socket_to_job[ job['socket'] ] = []

        self.socket_to_job[ job['socket'] ].append(job)

    def add_in_job(self, job):
        #Logger().debug("Adding incoming job")
        super(TCPCommunicationHandler, self).add_in_job(job)

        if job['socket']:
            self.sockets_in.append(job['socket'])

    def remove_out_job(self, job):
        super(TCPCommunicationHandler, self).remove_out_job(job)
        return self.socket_to_job[ job['socket'] ].remove(job)

    def jobs_by_socket(self, socket):
        try:
            return self.socket_to_job[ socket ]
        except KeyError:
            Logger().error("No job was found by the socket")
            print "Socket: ", socket
            print "Socket to job list", self.socket_to_job

    def run(self):
        # Starting the select on the sockets. We're setting a timeout
        # so we can break and test if we should break out of the thread
        # if somebody have called finalize. 
        it = 0 #iteration counter
        while True:
            try:
                if super(TCPCommunicationHandler, self).shutdown_ready():
                    break

                it += 1
                (in_list, out_list, _) = select.select( self.sockets_in, self.sockets_out, [], 1)
                
                for read_socket in in_list:
                    # There are both bound sockets and active connections in the 
                    # in list. We try to accept (if it's a bound socket) and if
                    # not we know we can just use the connection. 
                    try:
                        (conn, sender_address) = read_socket.accept()
                        in_list.append(conn)
                    except socket.error:
                        conn = read_socket

                    tag, sender, communicator, recv_type, data = structured_read(conn)
                    self.callback(callback_type="recv", tag=tag, sender=sender, communicator=communicator, recv_type=recv_type, data=data)

                # We handle write operations second (for no reason).
                i = 0
                for client_socket in out_list:
                    i += 1
                    jobs = self.jobs_by_socket(client_socket)
                    for job in jobs:
                        if job['status'] == 'ready':
                            # Send the data to the receiver. This should probably be rewritten so it 
                            # pickles the clean data and sends the tag and data-lengths, update the job
                            # and wait for the answer to arive on the reading socket. 
                            data = pickle.dumps(job['data'],protocol=-1)
                            
                            # FIXME: Insert these header information 
                            recv_type = 42
                            header = pack_header( self.rank, job['tag'], len(data), job['communicator'].id, recv_type )

                            job['socket'].send( header + data )
                            Logger().info("Sending data on the socket. Going to call the callbacks")

                            # Trigger the callbacks. 
                            # FIXME: The callback should also include the sender / receiver of the data.
                            
                            l = Logger()
                            l.debug("="*60)
                            l.debug(job.__repr__())
                            l.debug(job['communicator'].__repr__())
                            l.debug("="*60)
                            
                            self.callback(job, status='ready', ffrom="socket-outlist, tcp.py 244ish+1->225ish - ish => 255")
                            job['status'] = 'finished'

                            self.remove_out_job(job)

            except select.error, e:
                print e
                break
            
class SocketPool(object):
    """
    This class manages a pool of socket connections. You request and deletes
    connections through this class.
    
    The class have room for a number of cached socket connections, so if you're
    connection is heavily used it will probably not be removed. This way your
    call will not create and teardown the connection all the time. 
    
    NOTE: The number of cached elements are controlled through the constants 
    module, even though it might be exposed at a later point through command
    line arguments for mpirun.py
    
    NOTE 2: It's possible to mark a connections as mandatory persistent. This
    will not always give you nice performance. Please don't use this feature
    do much as it can push other connections out of the cache. And these
    connections might be more important and your custom one.
    
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
        a black box that will cache your connections when it's 
        possible.
        """
        client_socket = self._get_rank(rank)
        created = False
        if not client_socket:
            receiver = (socket_host, socket_port)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( receiver )
            
            if len(self.sockets) == self.max_size:
                self._remove_element()
                
            # Add the element to the list
            self._add(rank, client_socket, force_persistent)
            created = True
        return client_socket, created

    def _remove_element(self):
        """
        Finds the first element that already had it's second change. 
        Remove it from the list
        """
        for x in range(2):
            for socket in self.sockets:
                (srank, sreference, force_persistent) = self.metainfo[socket]
                if force_persistent:
                    continue
                
                if sreference:
                    self.metainfo[socket] = (srank, False, force_persistent)
                else:
                    self.sockets.remove(socket)
                    del self.metainfo[socket]
                    break

        raise MPIException("Not possible to add a socket connection to the internal caching system. There is %d persistant connections and they fill out the cache" % self.max_size)
    
    def _get_rank(self, rank):
        """
        Trieds to find a connection for a specific
        rank. If not possible we return None
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
    
class TCPNetwork(AbstractNetwork):

    def __init__(self, options):
        # Initialize the socket pool. We'll use it to get / remove socket connections
        self.socket_pool = SocketPool(constants.SOCKET_POOL_SIZE)
        
        super(TCPNetwork, self).__init__(TCPCommunicationHandler, options)
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.socket = socket

        print "I'm on %s and %d" % (hostname, port_no)

        # Do the initial handshaking with the other processes
        self.handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))

        # Give the inboundand outbound thread access to the socket
        # connection pool.
        self.t_in.socket_pool = self.socket_pool
        self.t_out.socket_pool = self.socket_pool

    def set_mpi_world(self, MPI_COMM_WORLD):
        self.MPI_COMM_WORLD = MPI_COMM_WORLD

        # Manually add a "always-on"/daemon socket on the right thread.
        job = {'type' : "world", 'socket' : self.socket, 'status' : 'new', 'persistent': True}

        self.t_in.add_in_job( job )

#        self.start_job(None, MPI_COMM_WORLD, "world", None, None, None, self.socket)

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
        
    def start_job(self, request, communicator, jobtype, participant, tag, data, socket=None, callbacks=[]):
        """
        Used to create a specific job structure for the TCP layer. This involves setting
        up an initial job structure and passing it to the correct thread. 

        The job structure is initialized without a socket. If it's a send request a socket
        will be created by the outgoing thread. If it's a receive request we'll wait for the
        daemon socket to get an accept and get a socket from there. 

        FIXME: Do we create a job structure at all for receiving requests? There are already
        a request object. Why not just create it when we make the accept on the daemon socket
        and then match it on the pending requests later on?
        """
        Logger().debug("Starting a %s network job with tag %s and %d callbacks" % (jobtype, tag, len(callbacks)))

        global_rank = communicator.group().members[participant]['global_rank']
        
        Logger().info("Starting a job with global rank %d" % global_rank)
            
        job = {
               'type' : jobtype, 
               'global_rank' : global_rank, 
               'tag' : tag, 
               'data' : data, 
               'socket' : socket, 
               'request' : request, 
               'status' : 'new', 
               'callbacks' : callbacks, 
               'communicator' : communicator, 
               'persistent': False,
               'participant' : communicator.comm_group.members[participant]
        } 

        self.t_out.add_out_job( job )

    def finalize(self):
        # Call the finalize in the parent class. This will handle
        # proper shutdown of the communication threads (in/out).
        super(TCPNetwork, self).finalize()

        self.socket.close()
