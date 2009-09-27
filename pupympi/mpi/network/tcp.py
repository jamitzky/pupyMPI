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
    """
    Return the format and size of the header format.
    The format for a 32bit architecture is used as a basis. By
    finding the actual multiplier the number of padding bytes is
    determined. Ie.
    
    x64: 
        bit_multiplier = 2    # As a long takes but 8 bytes
        padbytes = (2-1)*(5*8/2) => 20. Ie. we'll but 20 
                        pad bytes in there which will double
                        the data as expected by doubling the
                        the bitsize
    x128:
         bit_multiplier = 4
         padbytes = (4-1)*(5*16/4) => 60. Ie. we'll but 60 
                        pad bytes in there which will x4
                        the data as expected by x4 the
                        the bitsize
    """
    format_32 = "lllll"
    bit_multiplier = struct.calcsize("l") / 4
    padbytes = (bit_multiplier-1)*(struct.calcsize(format_32)/bit_multiplier)
    format = format_32 + "x"*padbytes
    return (format, struct.calcsize(format) )
    
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

    #Logger().debug("Starting receive first loop")

    # get the header
    while not header_unpacked:
        data += socket_connection.recv(header_size)
        
        # NOTE: Shouldn't it be >= header_size here?
        if len(data) > header_size:
            sender, tag, msg_size, communicator, recv_type = unpack_header(data)
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

    #Logger().debug("Done with tag(%s), sender(%s) and data(%s)" % (tag, sender, data))

    return tag, sender, communicator, recv_type, data

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
            raise e
            logger.debug("get_socket: Permission error on port %d" % port_no)
            used.append( port_no ) # Mark socket as used (or no good or whatever)

    #logger.debug("get_socket: Bound socket on port %d" % port_no)
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
        #Logger().debug("TCPCommunication handler initialized")
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
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( receiver )
            self.sockets_out.append(client_socket)
            job['socket'] = client_socket
        job['status'] = 'ready'

        # Tag the socket with a job so we can find it again
        self.socket_to_job[ job['socket'] ] = job

    def add_in_job(self, job):
        #Logger().debug("Adding incoming job")
        super(TCPCommunicationHandler, self).add_in_job(job)

        if job['socket']:
            self.sockets_in.append(job['socket'])

    def job_by_socket(self, socket):
        try:
            return self.socket_to_job[ socket ]
        except KeyError:
            Logger().debug("No job was found by the socket")

    def run(self):
        #Logger().debug("Starting select loop in TCPCommunicatorHandler")

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
                
                # Not so much debug please, let's see first 2 then every 10th until 12 then every 1000th            
                # Fixme: Make general debugger stuff in the logger so the logger knows not to print everything
                # jan: quick hack to decrease spam
                #if it < 3 or (it < 10000 and it % 1000 == 0) or (it % 100000 == 0):
                #    Logger().debug("Iteration %d in TCPCommunicationHandler. There are %d read sockets and %d write sockets. Selected %d in-sockets and %d out-sockets." % (it, len(self.sockets_in), len(self.sockets_out), len(in_list), len(out_list)))

                # We handle read operations first
                for read_socket in in_list:
                    (conn, sender_address) = read_socket.accept()

                    tag, sender, communicator, recv_type, data = structured_read(conn)
                    self.callback(callback_type="recv", tag=tag, sender=sender, communicator=communicator, recv_type=recv_type, data=data)

                # We handle write operations second (for no reason).
                for client_socket in out_list:
                    job = self.job_by_socket(client_socket)
                    if job['status'] == 'ready':
                        # Send the data to the receiver. This should probably be rewritten so it 
                        # pickles the clean data and sends the tag and data-lengths, update the job
                        # and wait for the answer to arive on the reading socket. 
                        data = pickle.dumps(job['data'])
                        
                        # FIXME: Insert these header information 
                        recv_type = 42
                        header = pack_header( self.rank, job['tag'], len(data), job['communicator'].id, recv_type )

                        job['socket'].send( header + data )
                        Logger().info("Sending data on the socket. Going to call the callbacks")

                        # Trigger the callbacks. 
                        # FIXME: The callback should also include the sender / receiver of the data.
                        self.callback(job, status='ready')
                        job['status'] = 'finished'

            except select.error, e:
                Logger().info("Got an select error in the TCPCommunicationHandler select call: %s" % e)
            except socket.error, e:
                Logger().info("Got an socket error in the TCPCommunicationHandler select call: %s" % e)
        
class TCPNetwork(AbstractNetwork):

    def __init__(self, options):
        # FIXME: Should this socket be started by the actual job? Otherwise it's the only
        #        socket started before the job is created. 
        super(TCPNetwork, self).__init__(TCPCommunicationHandler, options)
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.socket = socket
        #Logger().debug("Network started on port %s. Currently active threads %d." % (port_no, activeCount()))
        

        # Do the initial handshaking with the other processes
        self.handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))

    def set_mpi_world(self, MPI_COMM_WORLD):
        self.MPI_COMM_WORLD = MPI_COMM_WORLD

        # Manually add a "always-on"/daemon socket on the right thread.
        self.start_job(None, MPI_COMM_WORLD, "world", None, None, None, self.socket)

    def handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        #Logger().debug("handshake: Communicating ports and hostname to mpirun")
        
        # Packing the data
        data = pickle.dumps( (self.hostname, self.port, internal_rank ) )
        
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

        job = {'type' : jobtype, 'tag' : tag, 'data' : data, 'socket' : socket, 'request' : request, 'status' : 'new', 'callbacks' : callbacks, 'communicator' : communicator, 'persistent': False}

        if participant is not None:
            job['participant'] = communicator.comm_group.members[participant]

        #Logger().debug("Network job structure created. Adding it to the correct thead by relying on inherited magic.")

        if jobtype in ("bcast_send", "send"):
            self.t_out.add_out_job( job )
        elif jobtype == "world":
            self.t_in.add_in_job( job )

    def finalize(self):
        # Call the finalize in the parent class. This will handle
        # proper shutdown of the communication threads (in/out).
        super(TCPNetwork, self).finalize()

        self.socket.close()
        #logger = Logger().debug("The TCP network is closed")

    def barrier(self, comm):
        # TODO Implement
        pass
