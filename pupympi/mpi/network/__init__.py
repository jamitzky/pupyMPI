import socket, threading, struct, select

try:
    import cPickle as pickle
except ImportError:
    import pickle


import time


from mpi.exceptions import MPIException
from mpi.network.socketpool import SocketPool
from mpi.network import utils # Some would like the rest of the utils to be more explicitly used ... maybe later
from mpi.network.utils import get_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.logger import Logger

class Network(object):
    def __init__(self, mpi, options):

        if options.disable_full_network_startup:
            socket_pool_size = options.socket_pool_size
        else:
            socket_pool_size = options.size

        self.socket_pool = SocketPool(socket_pool_size)

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
        
        self.full_network_startup = not options.disable_full_network_startup

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
        utils.robust_send(s_conn, prepare_message(data, internal_rank))        
        
        # Receiving data about the communicator, by unpacking the head etc.
        rank, raw_data = get_raw_message(s_conn)
        data = pickle.loads(raw_data)
        (_, _, _, all_procs) = data

        s_conn.close()

        self.all_procs = {}

        for (host, port, global_rank) in all_procs:
            self.all_procs[global_rank] = {'host' : host, 'port' : port, 'global_rank' : global_rank}

    def start_full_network(self):
        if self.full_network_startup:
            #Logger().debug("Starting a full network startup")

            # We make a full network startup by receiving from all with lower ranks and 
            # send to higher ranks
            our_rank = self.mpi.MPI_COMM_WORLD.rank()
            size = self.mpi.MPI_COMM_WORLD.size()

            receiver_ranks = [x for x in range(0, our_rank) if x != our_rank]
            sender_ranks = range(our_rank+1, size)

            Logger().debug("Full network startup with receiver_ranks (%s) and sender_ranks (%s)" % (receiver_ranks, sender_ranks))

            recv_handles = []
            # Start all the receive 
            for r_rank in receiver_ranks:
                handle = self.mpi.MPI_COMM_WORLD.irecv(r_rank, constants.MPI_TAG_FULL_NETWORK)
                recv_handles.append(handle)
            
            #Logger().debug("Start_full_network: All recieves posted")

            # Send all
            for s_rank in sender_ranks:
                self.mpi.MPI_COMM_WORLD.send(s_rank, our_rank, constants.MPI_TAG_FULL_NETWORK)

            #Logger().debug("Start_full_network: All sends done")

            # Finish the receives
            for handle in recv_handles:
                handle.wait()
            
            # NOTE: What is the effect of this? Doesn't it make the socketpool static?
            self.socket_pool.readonly = True
        
        # DEBUG NOTE
        # Procs that hang never get to here, they hang while finishing the recieves
        Logger().debug("Network (fully) started")

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
        #Logger().debug("Network got finalize call")
        Logger().debug("Finalize unstarted calls: %s" % self.mpi.unstarted_requests)
        Logger().debug("Finalize pending_requests: %s" % self.mpi.pending_requests)
        #time.sleep(10) # FIXME: We want to try without this one!
        self.t_in.finalize()

        if not self.options.single_communication_thread:
            self.t_out.finalize()
        
        # DEBUG TEST
        # Try to make them die thread die
        self.t_in.join()
        self.t_out.join()
        
        Logger().debug("network.finalize: DONE Finalize")
        # NOTE: Why does this fail a lot in TEST_finalize_quickly? Why can we not afford to be "interrupted" here?
        #time.sleep(2)
        
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
        
        # Locks for proper access to the internal socket->request structure
        self.socket_to_request_lock = threading.Lock()
        
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

        with self.socket_to_request_lock:
            self.network.t_out.socket_to_request[client_socket].append(request) # socket already exists just add another request to the list


    def add_in_socket(self, client_socket):
        self.sockets_in.append(client_socket)
        
    def add_out_socket(self, client_socket):
        with self.socket_to_request_lock:
            self.socket_to_request[client_socket] = []
            
        self.sockets_out.append(client_socket)
    
    def close_all_sockets(self):
        # DEBUG
        n = 0
        m = 0
        # NOTE:
        # Maybe we should only attempt to close either outgoing OR ingoing sockets
        # FIXME: This sleep is a hack, which we need when dynamic socket pool is not enabled
        #time.sleep(4)
        #time.sleep(2)
        
        
        for s in self.sockets_in + self.sockets_out:            
            try:
                #s.shutdown(0)   # Further receives are disallowed
                #s.shutdown(1)   # Further sends are disallowed.
                #s.shutdown(2)   # Further sends and receives are disallowed.
                s.close()
                n += 1
            except Exception, e:
                m += 1
                Logger().debug("Got error when closing socket: %s" % e)
         
        # DEBUG
        # sleeping here does not really help
        #time.sleep(4)
        
        #Logger().debug("close_all_sockets: %i sockets closed, %i sockets gave exception. Ins: %i, Outs: %i" % (n,m, len(self.sockets_in), len(self.sockets_out) ))
    
    def run(self):
        
        def _select():
            try:
                return select.select( self.sockets_in, self.sockets_out, self.sockets_in + self.sockets_out, 1)
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
        
        def _handle_readlist(readlist):
            for read_socket in readlist:
                add_to_pool = False
                try:
                    (conn, sender_address) = read_socket.accept()

                    self.network.t_in.add_in_socket(conn)
                    self.network.t_out.add_out_socket(conn)
                    add_to_pool = True
                    Logger().debug("Accepted connection on the main socket")
                except socket.error, e:
                    # We try to accept on all sockets, even ones that are already in use.
                    # This means that if accept fails it is normally just data coming in
                    #Logger().debug("accept() threw: %s for socket:%s" % (e,read_socket) )
                    conn = read_socket
                
                try:
                    rank, raw_data = get_raw_message(conn)
                except MPIException, e:                    
                    # Broken connection is ok when shutdown is going on
                    if self.shutdown_event.is_set():
                        Logger().debug("_handle_readlist -> get_raw_message -> recieve_fixed -> recv (SHOT DOWN) threw: %s" % e)
                        continue
                    else:
                        Logger().debug("_handle_readlist: Broken connection or worse. Error was: %s" % e)
                except Exception, e:
                    Logger().error("_handle_readlist: Unexpected error thrown from get_raw_message. Error was: %s" % e)
                    
                Logger().debug("Received data from rank %d" % rank)
                data = pickle.loads(raw_data)
                
                if add_to_pool:
                    self.network.socket_pool.add_created_socket(conn, rank)
                
                # Signal mpi thread that there is new receieved data
                with self.network.mpi.has_work_cond:
                    with self.network.mpi.raw_data_lock:
                        self.network.mpi.has_work_cond.notify()
                        self.network.mpi.raw_data_queue.append(raw_data)
                        self.network.mpi.raw_data_event.set()
         
        def _handle_writelist(writelist):
            for write_socket in writelist:
                removal = []
                with self.socket_to_request_lock:
                    request_list = self.socket_to_request[write_socket]
                for request in request_list:
                    if request.status == "cancelled":
                        removal.append((socket, request))
                    elif request.status == "new":                        
                        Logger().debug("Starting data-send on %s. request: %s" % (write_socket, request))
                        # Send the data on the socket
                        try:
                            # TODO: We should loop here 
                            #write_socket.send(request.data)
                            utils.robust_send(write_socket,request.data)
                        except socket.error, e:
                            Logger().error("send() threw:%s for socket:%s with data:%s" % (e,write_socket,request.data ) )
                            # Send went wrong, do not update, but hope for better luck next time
                            continue
                            
                        removal.append((write_socket, request))
                        request.update("ready") # update status and signal anyone waiting on this request
                    else:
                        # This seems to happen with the "finished" state a lot of times. It should not happen
                        # as it might conclude that a request is changing it's state when it's not supposed
                        # to
                        pass
                        #Logger().warning("The socket select found an invalid request status: %s, type (%s), tag(%s) participant(%d)" % 
                        #        (request.status, request.request_type, request.tag, request.participant))
                        
                # Remove the requests (messages) that was successfully sent from the list for that socket
                if removal:  
                    with self.socket_to_request_lock:
                        for (write_socket,matched_request) in removal:
                            self.socket_to_request[write_socket].remove(matched_request)

        while not self.shutdown_event.is_set():
            (in_list, out_list, error_list) = _select()
 
            _handle_readlist(in_list)
            _handle_writelist(out_list)
        
        # The shutdown events is called, so we're finishing the network. This means
        # flushing all the send jobs we have and then close the sockets.
        while self.socket_to_request:
            (in_list, out_list, error_list) = _select()
            _handle_writelist(out_list)

            removal = []
            for wsocket in self.socket_to_request:
                if not self.socket_to_request[wsocket]:
                    removal.append(wsocket)
            
            for r in removal:
                del self.socket_to_request[r]
        
        # The above loop only breaks when the send structure is empty, ie there are no more
        # requests to be send. We can therefore close the sockets. 
        self.close_all_sockets()   

    def finalize(self):
        self.shutdown_event.set()
        Logger().debug("Communication handler closed by finalize call, socket_to_request: %s" % self.socket_to_request)
