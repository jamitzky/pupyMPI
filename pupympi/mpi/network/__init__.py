import socket, threading, struct, select

try:
    import cPickle as pickle
except ImportError:
    import pickle
from time import time

from mpi.exceptions import MPIException
from mpi.network.socketpool import SocketPool
from mpi.network.utils import get_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.logger import Logger

class Network(object):
    def __init__(self, mpi, options):
        self.socket_pool = SocketPool(constants.SOCKET_POOL_SIZE)

        self.mpi = mpi
        self.options = options
        self.t_in = CommunicationHandler(self, options.rank, self.socket_pool)
        self.t_in.daemon = True
        self.t_in.start()
        
        if options.single_communication_thread:
            self.t_out = self.t_in
        else:
            self.t_out = CommunicationHandler(self, options.rank, self.socket_pool)
            self.t_out.daemon = True
            self.t_out.start()
        
        (socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        socket.listen(5)
        self.main_receive_socket = socket
        
        self.t_in.sockets_in.append(self.main_receive_socket)
        
        # Do the initial handshaking with the other processes
        self._handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))

    def _handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method create the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.
        
        For mpirun to have this information we first send all the data
        from our own process. So we bind a socket. 
        """
        # Packing the data
        data = (self.hostname, self.port, internal_rank )
        
        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        #Logger().debug("Trying to connect to (%s,%s)" % recipient)
        s_conn.connect(recipient)
        
        # Pack the data with our special format
        data = (-1, -1, constants.TAG_INITIALIZING, data)
        s_conn.send(prepare_message(data))
        
        # Receiving data about the communicator, by unpacking the head etc.
        data = pickle.loads(get_raw_message(s_conn))
        (_, _, _, all_procs) = data

        s_conn.close()

        self.all_procs = {}
        print all_procs
        for (host, port, global_rank) in all_procs:
            self.all_procs[global_rank] = {'host' : host, 'port' : port, 'global_rank' : global_rank}

    def start_collective(self, request, communicator, jobtype, data, callbacks=[]):
        Logger().info("Starting a %s collective network job with %d callbacks" % (type, len(callbacks)))
        
        job = {'type' : jobtype, 'data' : data, 'request' : request, 'status' : 'new', 'callbacks' : callbacks, 'communicator' : communicator, 'persistent': True}
        tree = BroadCastTree(range(communicator.size()), communicator.rank())
        tree.up()
        tree.down()
        
    def find_global_rank(self, hostname, portno):
        for member in self.mpi.MPI_COMM_WORLD.group().members.values():
            if member['host'] == hostname and member['port'] == portno:
                return member['global_rank']

    def finalize(self):
        """
        Forwarding the finalize call to the threads. Look at the 
        CommunicationHandler.finalize for a deeper description of
        the shutdown procedure. 
        """
        Logger().debug("Network got finalize call")
        self.t_in.finalize()
        if not self.options.single_communication_thread:
            self.t_out.finalize()
        self.main_receive_socket.close()
        
class CommunicationHandler(threading.Thread):
    """
    This is a single thread doing both in and out or there are two threaded instances one for each
    """
    def __init__(self,network, rank, socket_pool):
        super(CommunicationHandler, self).__init__()
        
        # Store all procs in the network for lookup
        self.network = network
        
        # Add two TCP specific lists. Read and write sockets
        self.sockets_in = []
        self.sockets_out = []
        
        # Structure for finding request objects from a socket connection.
        # a dict mapping a socket key to a list of requests on that socket
        self.socket_to_request = {}
        
        self.rank = rank
        self.socket_pool = socket_pool
        
        self.shutdown_event = threading.Event()
    
    def add_out_request(self, request):
        # Find the global rank of other party
        global_rank = request.communicator.group().members[request.participant]['global_rank']
        
        # Find a socket and port of other party           
        host = self.network.all_procs[global_rank]['host']
        port = self.network.all_procs[global_rank]['port']
        
        # Create the proper data structure and pickle the data
        data = (request.communicator.id, request.communicator.rank(), request.tag, request.data)
        request.data = prepare_message(data)

        client_socket, newly_created = self.socket_pool.get_socket(global_rank, host, port)
        if newly_created:
            self.network.t_in.sockets_in.append(client_socket)
            self.network.t_out.sockets_out.append(client_socket)
        
        # Add the socket and request to the internal system
        if socket in self.socket_to_request:
            self.socket_to_request[client_socket].append(request) # socket already exists just add another request to the list
        else:
            self.socket_to_request[client_socket] = [ request ] # new socket, add the request in a singleton list
            
    def remove_request(self, socket, request):
        """
        For now we try to remove the request from all lists not just the right socket's list
        This is handled by except, but could be done nicer.    
        """
        self.socket_to_request[socket].remove(request)
    
    def run(self):
        while not self.shutdown_event.is_set():
            
            (in_list, out_list, _) = select.select( self.sockets_in, self.sockets_out, [], 1)
            
            Logger().debug("In select loop inlist: %s  outlist: %s" % (in_list,out_list))
            should_signal_work = False
            for read_socket in in_list:
                Logger().debug("In recieve loop")
                try:
                    (conn, sender_address) = read_socket.accept()
                    self.sockets_in.append(conn)
                    
                    # Look through our network details to find the rank of the
                    # other side of this newly created socket. Then add it manually
                    # to the socket pool.
                    global_rank = self.network.find_global_rank(*sender_address)
                    self.network.socket_pool.add_created_socket(conn, global_rank)
                except socket.error:
                    conn = read_socket

                should_signal_work = True
                
                raw_data = get_raw_message(conn)
                
                with self.network.mpi.raw_data_lock:
                    self.network.mpi.raw_data_queue.append(raw_data)
                self.network.mpi.raw_data_event.set()
            
            for write_socket in out_list:
                #Logger().debug("Found socket in out-list")
                removal = []
                request_list = self.socket_to_request[write_socket]
                for request in request_list:
                    if request.status == "cancelled":
                        removal.append((socket, request))
                    elif request.status == "new":
                        Logger().debug("Sending data on socket")
                        # Send the data on the socket
                        write_socket.send(request.data)
                        removal.append((write_socket, request))
                        request.update("ready")
                    else:
                        raise Exception("We got a status in the send socket select we don't handle.. it's there--> %s" % request.status)
                
                if removal:
                    should_signal_work = True
                    
                for t in removal:
                    self.remove_request(*t)
                    
            # Signal to the MPI run() method that there is work to do
            if should_signal_work:
                with self.network.mpi.has_work_cond:
                    self.network.mpi.has_work_cond.notify()
            
    def finalize(self):
        Logger().debug("Communication handler closed by finalize call")
        self.shutdown_event.set()