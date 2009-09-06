import mpi, time, socket, threading, random, select, struct
from mpi.logger import Logger
from mpi.network import AbstractNetwork, AbstractCommunicationHandler
from threading import Thread, activeCount

try:
    import cPickle as pickle
except ImportError:
    import pickle

def structured_read(socket_connection):
    """
    Read an entire message from a socket connection
    and returns the tag, sender rank and message. 
    
    The stucture of all the MPI message consists
    of a fixed size header and a variable length message.
    
    The header has 3 fields:
        sender      : integer
        tag         : integer
        msg_size    : integer

    The method is constructed of two loops. The first loop
    readys until we have received the entire header. The
    contents of the header is then unpacked. The unpacked
    msg_size is used to receive the rest of the message. 

    The size of the header is 12 bytes according to this
    python code:

    >>> import struct
    >>> struct.calcsize("lll")
    12

    Which also means that we're packing data as longs, so 
    we have room for a lot of data in the message. 
    """
    HEADER_SIZE = 12
    header_unpacked = False

    # The end variables we're gonna return
    tag = sender = None
    data = ''

    Logger().debug("Starting receive first loop")

    while not header_unpacked:
        data += socket_connection.recv(HEADER_SIZE)
        
        # NOTE:
        # on my list of dumb-ass questions why the tagged on "not header_unpacked"?
        # it can only be set to true inside the if-statement so the check seems
        # superflous
        # - Fred
        if len(data) > HEADER_SIZE and not header_unpacked:
            sender, tag, msg_size = struct.unpack("lll", data[:HEADER_SIZE])
            header_unpacked = True

    
    # receive the rest of the data 
    total_msg_size = msg_size + HEADER_SIZE
    recv_size = msg_size

    Logger().debug("Starting receive second loop with total_msg_size(%d) and recv_size(%d)" %(total_msg_size, recv_size))

    while len(data) < total_msg_size:
        recv_size = total_msg_size - len(data)
        data += socket_connection.recv(recv_size)
    
    # unpacking the data
    data = pickle.loads(data[HEADER_SIZE:])

    Logger().debug("Done with tag(%s), sender(%s) and data(%s)" % (tag, sender, data))

    return tag, sender, data

def get_socket(range=(10000, 30000)):
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
            used.append( port_no ) # Mark socket as used (or no good or whatever)

    logger.debug("get_socket: Bound socket on port %d" % port_no)
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
    """

    def __init__(self, *args, **kwargs):
        Logger().debug("TCPCommunication handler initialized")
        super(TCPCommunicationHandler, self).__init__(*args, **kwargs)

        # Add two TCP specific lists. Read and write sockets
        self.sockets_in = []
        self.sockets_out = []

        self.socket_to_job = {}
        self.received_data = {}

    def add_received_data(self, tag, data):
        """
        Saves received data in a structure organised by tag (later
        also communicator) so it's easy to find.
        """
        Logger().info("Adding recived data with tag %s" % tag)
        if tag not in self.received_data:
            self.received_data[tag] = []

        self.received_data[tag].append(data)

    def get_received_data(self, participant, tag, communicator):
        Logger().info("Asking about data with tag %s" % tag)
        # FIXME: Handle the tag and participant
        if tag in self.received_data:
            try:
                return self.received_data[tag].pop(0)
            except IndexError:
                pass

    def add_out_job(self, job):
        super(TCPCommunicationHandler, self).add_out_job(job)
        Logger().debug("Adding outgoing job")

        # This is a sending operation. We should create a socket 
        # for the job, so we can select from it later. 
        receiver = ( job['participant']['host'], job['participant']['port'],)
        if not job['socket']:
            # Create a client socket and connect to the other end
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( receiver )
            self.sockets_out.append(client_socket)
            job['socket'] = client_socket
        job['status'] = 'ready'

        # Tag the socket with a job so we can find it again
        self.socket_to_job[ job['socket'] ] = job

    def add_in_job(self, job):
        Logger().debug("Adding incomming job")
        super(TCPCommunicationHandler, self).add_in_job(job)

        if job['socket']:
            self.sockets_in.append(job['socket'])

    def job_by_socket(self, socket):
        try:
            return self.socket_to_job[ socket ]
        except KeyError:
            Logger().debug("No job was found by the socket")

    def run(self):
        Logger().debug("Starting select loop in TCPCommunicatorHandler")

        # Starting the select on the sockets. We're setting a timeout
        # so we can break and test if we should break out of the thread
        # if somebody have called finalize. 
        it = 0
        while True:
            try:
                if super(TCPCommunicationHandler, self).shutdown_ready():
                    break

                it += 1
                (in_list, out_list, _) = select.select( self.sockets_in, self.sockets_out, [], 1)
                
                #Not so much debug please, let's see first 2 then every 10th until 12 then every 1000th            
                if it < 3 or (it < 100 and it % 10 == 0) or (it % 1000 == 0):
                    Logger().debug("Iteration %d in TCPCommunicationHandler. There are %d read sockets and %d write sockets. Selected %d in-sockets and %d out-sockets." % (it, len(self.sockets_in), len(self.sockets_out), len(in_list), len(out_list)))

                # We handle read operations first
                for read_socket in in_list:
                    (conn, sender_address) = read_socket.accept()

                    # Fixme. This should be done in a two loop way
                    tag, sender, data = structured_read(conn)

                    # Save the data in an internal structure so we can find it again. 
                    # FIXME: We should add the communicator id, name or whatever. Otherwise
                    # messages to different communicators might overlap
                    self.add_received_data(tag, data)

                # We handle write operations second (for no reason).
                for client_socket in out_list:
                    job = self.job_by_socket(client_socket)
                    if job['status'] == 'ready':
                        # Send the data to the receiver. This should probably be rewritten so it 
                        # pickles the clean data and sends the tag and data-lengths, update the job
                        # and wait for the answer to arive on the reading socket. 
                        data = pickle.dumps(job['data'])
                        header = struct.pack("lll", self.rank, job['tag'], len(data))

                        job['socket'].send( header + data )
                        Logger().info("Sending data on the socket. Going to update the request object next")

                        job['request'].update(status='ready')
                        job['status'] = 'finished'

            except select.error, e:
                Logger().warning("Got an select error in the TCPCommunicationHandler select call: %s" % e.message)
            except socket.error, e:
                Logger().warning("Got an socket error in the TCPCommunicationHandler select call: %s" % e.message)
        
class TCPNetwork(AbstractNetwork):

    def __init__(self, options):
        super(TCPNetwork, self).__init__(TCPCommunicationHandler, options)
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.socket = socket
        Logger().debug("Network started on port %s. Currently active threads %d." % (port_no, activeCount()))
        

        # Do the initial handshaking with the other processes
        self.handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))

    def set_mpi_world(self, MPI_COMM_WORLD):
        self.MPI_COMM_WORLD = MPI_COMM_WORLD

        # Manually add the daemon socket on the right thread.
        self.start_job(None, MPI_COMM_WORLD, "daemon", None, None, None, self.socket)

    def handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        Logger().debug("handshake: Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ) )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        Logger().debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        s_conn.send(data)
        
        # Receiving data about the communicator
        all_procs = s_conn.recv(1024)
        all_procs = pickle.loads( all_procs )
        Logger().debug("handshake: Received information for all processes (%d)" % len(all_procs))
        s_conn.close()

        self.all_procs = {}
        for (host, port, rank) in all_procs:
            self.all_procs[rank] = {'host' : host, 'port' : port, 'rank' : rank}

    def start_job(self, request, communicator, type, participant, tag, data, socket=None):
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
        Logger().debug("Starting a %s network job with tag %s" % (type, tag))

        job = {'type' : type, 'tag' : tag, 'data' : data, 'socket' : socket, 'request' : request, 'status' : 'new'}

        if participant is not None:
            job['participant'] = communicator.members[participant]

        Logger().debug("Network job structure created. Adding it to the correct thead by relying on inherited magic.")

        if type == "send":
            self.t_out.add_out_job( job )
        elif type == "daemon":
            self.t_in.add_in_job( job )

    def finalize(self):
        # Call the finalize in the parent class. This will handle
        # proper shutdown of the communication threads (in/out).
        super(TCPNetwork, self).finalize()

        self.socket.close()
        logger = Logger().debug("The TCP network is closed")

    def barrier(self, comm):
        # TODO Implement
        pass
