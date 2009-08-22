import mpi, time, socket, threading, random
from mpi.logger import Logger
from mpi.network import Network, CommunicationHandler
from threading import Thread

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
    pass

class TCPNetwork(Network):

    def __init__(self, single_communication_thread=False):
        super(TCPNetwork, self).__init__(single_communication_thread=False, TCPCommunicationHandler)

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

    def barrier(self, comm):
        # TODO Implement
        pass
