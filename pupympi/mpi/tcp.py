import mpi, time, socket, threading, random
from mpi.logger import Logger
from mpi.network import Network, CommunicationHandler
from threading import Thread
import select

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

class TCPCommunicationHandler(CommunicationHandler):
    """
    This is the TCP implementation of the main CommunicationHandler. There
    will be one or two threads of this class.

    The main purpose of this class is to select on a read and writelist and
    and handle incomming / outgoing requests. 

    Whenever some job is completed the request object matching the job will
    be updated. 

    We also keep an internal queue of the jobs not mathing a request object 
    yet. Whenever a new request objects comes into the queue we look through
    the already finished TCP jobs to find a mathing one. In this case a recv()
    call might return almost without blocking.
    """

    def __init__(self, *args, **kwargs):
        Logger().debug("TCPCommunication handler initialized")
        super(TCPCommunicationHandler, self).__init__(*args, **kwargs)

        # Add two TCP specific lists. Read and write sockets
        self.sockets_in = []
        self.sockets_out = []

    def add_out_job(self, job):
        super(TCPCommunicationHandler, self).add_out_job(job)
        Logger().debug("Adding outgoing job")

        # This is a sending operation. We should create a socket 
        # for the job, so we can selet from it later. 
        # FIXME

    def add_in_job(self, job):
        Logger().debug("Adding incomming job")
        super(TCPCommunicationHandler, self).add_in_job(job)

        if job['socket']:
            self.sockets_in.append(job['socket'])

    def run(self):
        Logger().debug("Starting select loop in TCPCommunicatorHandler")

        # Starting the select on the sockets. We're setting a timeout
        # so we can break and test if we should break ouf of the thread
        # if somebody have called finalize. 
        it = 0
        while True:
            try:
                if super(TCPCommunicationHandler, self).shutdown_ready():
                    break

                it += 1
                (in_list, out_list, _) = select.select( self.sockets_in, self.sockets_out, [], 1)
                Logger().debug("Iteration %d in TCPCommunicationHandler. Selected %d in-sockets and %d out-sockets" % (it, len(in_list), len(out_list)))
            except select.error:
                Logger().warning("Got an select error in the TCPCommunicationHandler select call")
            except socket.error:
                Logger().warning("Got an socket error in the TCPCommunicationHandler select call")
        
class TCPNetwork(Network):

    def __init__(self, options):
        super(TCPNetwork, self).__init__(TCPCommunicationHandler, options)
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.socket = socket
        Logger().debug("Network started on port %s" % port_no)

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

        job = {'type' : type, 'tag' : tag, 'data' : data, 'socket' : socket, 'request' : request}
        if participant:
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
