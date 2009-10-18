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
        
        (server_socket, hostname, port_no) = get_socket()
        self.port = port_no
        self.hostname = hostname
        server_socket.listen(5)
        self.main_receive_socket = server_socket
        
        self.t_in.add_in_socket(self.main_receive_socket)
        
        Logger().debug("main socket is: %s" % server_socket)
        
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
        s_conn.send(prepare_message(data, internal_rank))
        
        # Receiving data about the communicator, by unpacking the head etc.
        rank, raw_data = get_raw_message(s_conn)
        data = pickle.loads(raw_data)
        (_, _, _, all_procs) = data

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
        Logger().debug("Network got finalize call")
        self.t_in.finalize()
        if not self.options.single_communication_thread:
            self.t_out.finalize()
        #self.main_receive_socket.close()
        
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
        """
        Put a requested out operation (eg. send) on the out list        
        """
        
        # Find the global rank of recipient process
        global_rank = request.communicator.group().members[request.participant]['global_rank']
        
        #Logger().debug("Out-request found global rank %d" % global_rank)
        
        # Find a socket and port of recipient process
        host = self.network.all_procs[global_rank]['host']
        port = self.network.all_procs[global_rank]['port']
        
        # Create the proper data structure and pickle the data
        data = (request.communicator.id, request.communicator.rank(), request.tag, request.data)
        request.data = prepare_message(data, request.communicator.rank())

        client_socket, newly_created = self.socket_pool.get_socket(global_rank, host, port)
        # If the connection is a new connection it is added to the socket lists of the respective thread(s)
        if newly_created:
            self.network.t_in.add_in_socket(client_socket)
            self.network.t_out.add_out_socket(client_socket)

        self.network.t_out.socket_to_request[client_socket].append(request) # socket already exists just add another request to the list


    def add_in_socket(self, client_socket):
        self.sockets_in.append(client_socket)
        
    def add_out_socket(self, client_socket):
        self.socket_to_request[client_socket] = []
        self.sockets_out.append(client_socket)
    
    def close_all_sockets(self):
        for s in self.sockets_in + self.sockets_out:
            try:
                s.close()
            except Exception, e:
                Logger.debug("Got error when closing socket: %s" % e)
    
    def run(self):
        while not self.shutdown_event.is_set():
            try:
                (in_list, out_list, error_list) = select.select( self.sockets_in, self.sockets_out, self.sockets_in + self.sockets_out, 1)
            except Exception, e:
                print "Got exception"
                print e
                print type(e)
                print self.sockets_in
                print self.sockets_out
                print "----- done ---------"
                print in_list
                print out_list
                print error_list
            
            
            for read_socket in in_list:
                add_to_pool = False
                try:
                    (conn, sender_address) = read_socket.accept()

                    self.network.t_in.add_in_socket(conn)
                    self.network.t_out.add_out_socket(conn)
                    add_to_pool = True
                except socket.error, e:
                    Logger().debug("accept() threw: %s for socket:%s" % (e,read_socket) )
                    conn = read_socket
                
                rank, raw_data = get_raw_message(conn)
                data = pickle.loads(raw_data)
                
                if add_to_pool:
                    self.network.socket_pool.add_created_socket(conn, rank)
                
                # Signal mpi thread that there is new receieved data
                with self.network.mpi.has_work_cond:
                    with self.network.mpi.raw_data_lock:
                        self.network.mpi.has_work_cond.notify()
                        self.network.mpi.raw_data_queue.append(raw_data)
                        self.network.mpi.raw_data_event.set()
            
            for write_socket in out_list:
                removal = []
                request_list = self.socket_to_request[write_socket]
                for request in request_list:
                    if request.status == "cancelled":
                        removal.append((socket, request))
                    elif request.status == "new":
                        Logger().debug("Starting data-send on %s. data: %s" % (write_socket, request.data))
                        # Send the data on the socket
                        try:
                            write_socket.send(request.data)
                        except socket.error, e:
                            Logger().error("send() threw:%s for socket:%s with data:%s" % (e,write_socket,request.data ) )
                            # Send went wrong, do not update, but hope for better luck next time
                            continue
                            
                        removal.append((write_socket, request))
                        request.update("ready") # update status and signal anyone waiting on this request
                    else:
                        raise Exception("We got a status in the send socket select we don't handle.. it's there--> %s" % request.status)
                
                # Remove the requests (messages) that was successfully sent from the list for that socket
                if removal:  
                    for (write_socket,matched_request) in removal:
                        self.socket_to_request[write_socket].remove(matched_request)
                    
        self.close_all_sockets()   

    def finalize(self):
        self.shutdown_event.set()
        Logger().debug("Communication handler closed by finalize call")
