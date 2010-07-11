#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
import socket, threading, struct, select, time

try:
    import cPickle as pickle
except ImportError:
    import pickle

from mpi.exceptions import MPIException
from mpi.network.socketpool import SocketPool
from mpi.network import utils # Some would like the rest of the utils to be more explicitly used ... maybe later
from mpi.network.utils import create_random_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.logger import Logger

def get_communicator_class(socket_poll_method=False):
    c_class = None

    if socket_poll_method:
        poll_method_exists = getattr(select, socket_poll_method, None)
        if not poll_method_exists:
            Logger().warn("Socket poll method '%s' is not supported on this system - falling back to automatic selection." % socket_poll_method)
            socket_poll_method = False

    if socket_poll_method == "epoll":
        c_class = CommunicationHandlerEpoll
    
    elif socket_poll_method == "kqueue":
        c_class = CommunicationHandlerKqueue

    elif socket_poll_method == "poll":
        c_class = CommunicationHandlerPoll

    elif socket_poll_method == "select":
        c_class = CommunicationHandlerSelect

    else:
        if socket_poll_method:
            Logger().warn("Unknown socket poll method '%s' - falling back to automatic selection." % socket_poll_method)

        epoll = getattr(select, "epoll", None)
        if epoll:
            c_class = CommunicationHandlerEpoll
    
        kqueue = getattr(select, "kqueue", None)
        if kqueue and not c_class:
            c_class = CommunicationHandlerKqueue

        poll = getattr(select, "poll", None)
        if poll and not c_class:
            c_class = CommunicationHandlerPoll
        
        if not c_class:
            c_class = CommunicationHandlerSelect
    
    #Logger().debug("Found communicator class of type %s, called with socket_poll_method parameter %s" % (c_class, socket_poll_method))
    return c_class

class Network(object):
    def __init__(self, mpi, options):

        if options.disable_full_network_startup:            
            socket_pool_size = options.socket_pool_size
            Logger().debug("Socket Pool DYNAMIC size:%i" % socket_pool_size)
        else:
            socket_pool_size = options.size
            Logger().debug("Socket Pool STATIC size:%i" % socket_pool_size)

        self.socket_pool = SocketPool(socket_pool_size)

        communicator_class = get_communicator_class(options.socket_poll_method)

        self.mpi = mpi
        self.options = options
        self.t_in = communicator_class(self, options.rank, self.socket_pool)
        self.t_in.daemon = True
        self.t_in.start()
        
        if options.single_communication_thread:
            self.t_out = self.t_in
            self.t_out.type = "combo"
        else:
            self.t_out = communicator_class(self, options.rank, self.socket_pool)
            self.t_out.daemon = True
            self.t_out.start()
            self.t_out.type = "out"
            self.t_in.type = "in"
        
        (server_socket, hostname, port_no) = create_random_socket()
        self.port = port_no
        self.hostname = hostname
        server_socket.listen(5)
        self.main_receive_socket = server_socket
        
        self.t_in.add_in_socket(self.main_receive_socket)
        
        #Logger().debug("main socket is: %s" % server_socket)
        
        # Do the initial handshaking with the other processes
        self._handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))
        
        self.full_network_startup = not options.disable_full_network_startup
        
        #global done
        #done = False

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
        # first _ is rank
        _, _, raw_data = get_raw_message(s_conn)
        data = pickle.loads(raw_data)
        (_, _, _, all_procs) = data

        s_conn.close()

        self.all_procs = {}

        for (host, port, global_rank) in all_procs:
            self.all_procs[global_rank] = {'host' : host, 'port' : port, 'global_rank' : global_rank}

    def start_full_network(self):
        # TODO: This condition should be moved up to caller and the whole function call made conditional in mpi/__init__.py
        if self.full_network_startup:
            Logger().debug("Starting a full network startup")

            # We make a full network startup by receiving from all with lower ranks and 
            # sending to higher ranks
            our_rank = self.mpi.MPI_COMM_WORLD.rank()
            size = self.mpi.MPI_COMM_WORLD.size()

            receiver_ranks = [x for x in range(0, our_rank)]
            sender_ranks = range(our_rank+1, size)

            #Logger().debug("Full network startup with receiver_ranks (%s) and sender_ranks (%s)" % (receiver_ranks, sender_ranks))

            recv_handles = []
            # Start all the receive 
            for r_rank in receiver_ranks:
                handle = self.mpi.MPI_COMM_WORLD.irecv(r_rank, constants.TAG_FULL_NETWORK)
                recv_handles.append(handle)
            
            #Logger().debug("Start_full_network: All recieves posted")

            # Send all
            for s_rank in sender_ranks:
                self.mpi.MPI_COMM_WORLD.send(our_rank, s_rank, constants.TAG_FULL_NETWORK)

            #Logger().debug("Start_full_network: All sends done")

            # Finish the receives
            for handle in recv_handles:
                handle.wait()
            
            #DEBUG
            #print "Socket pool sockets",self.socket_pool.sockets
            #print "Socket pool meta",self.socket_pool.metainfo
            # Full network start up means a static socket pool
            self.socket_pool.readonly = True
        
        #Logger().debug("Network (fully) started")

    def finalize(self):
        """
        Forwarding the finalize call to the threads. Look at the 
        CommunicationHandlerSelect.finalize for a deeper description of
        the shutdown procedure. 
        """
        #Logger().debug("Network got finalize call")
        #Logger().debug("Finalize unstarted calls: %s" % self.mpi.unstarted_requests)
        #Logger().debug("Finalize pending_requests: %s" % self.mpi.pending_requests)
        self.t_in.finalize()

        if not self.options.single_communication_thread:
            self.t_out.finalize()
        
        # Wait for network threads to die
        self.t_in.join()
        self.t_out.join()
        
        # Close socketpool
        self.socket_pool.close_all_sockets()

class BaseCommunicationHandler(threading.Thread):
    def __init__(self, network, rank, socket_pool):
        super(BaseCommunicationHandler, self).__init__()
        
        # Store all procs in the network for lookup
        self.network = network
        
        # Add two TCP specific lists. Read and write sockets
        self.sockets_in = []
        self.sockets_out = []
        
        # Structure for finding request objects from a socket connection.
        # a dict mapping a socket key to a list of requests on that socket
        self.socket_to_request = {}
        
        self.outbound_requests = 0 # Number of send requests queued (only acessed with socket_to_request_lock)
        self.rank = rank
        self.socket_pool = socket_pool
        
        self.type = "unset" # Will be set to "in","out" or "combo" and allow easy way of detecting role
        
        self.shutdown_event = threading.Event() # signal for shutdown        
        #self.outbound_requests_event = threading.Event() # signal for something to send
        
        
        
        # Locks for proper access to the internal socket->request structure and counter
        self.socket_to_request_lock = threading.Lock()

        # DEBUG
        self.debug_counter = 0

    def finalize(self):
        self.shutdown_event.set()        
        #Logger().debug("Communication handler (%s) closed by finalize call, socket_to_request: %s" % (self.type, self.socket_to_request) )

    def add_out_request(self, request):
        """
        Put a requested out operation (eg. send) on the out list        
        """
        # Find the global rank of recipient process
        global_rank = request.communicator.group().members[request.participant]['global_rank']
        
        # Find a socket and port of recipient process
        host = self.network.all_procs[global_rank]['host']
        port = self.network.all_procs[global_rank]['port']
        
        # Create the proper data structure and pickle the data
        data = (request.communicator.id, request.communicator.rank(), request.tag, request.acknowledge, request.data)
        #print "We found cmd: %d" % request.cmd
        request.data = prepare_message(data, request.communicator.rank(), cmd=request.cmd)
        
        ##Logger().warning("SHOW request %s" % request)
        
        #Logger().debug("rank:%i calling get_socket for globrank:%i" % (self.rank, global_rank))
        client_socket, newly_created = self.socket_pool.get_socket(global_rank, host, port)
        # If the connection is a new connection it is added to the socket lists of the respective thread(s)
        if newly_created:
            self.network.t_in.add_in_socket(client_socket)
            self.network.t_out.add_out_socket(client_socket)

        with self.socket_to_request_lock:
            try:
                self.network.t_out.socket_to_request[client_socket].append(request) # socket already exists just add another request to the list                
                self.outbound_requests += 1
            except Exception, e: # This should not happen
                Logger().error("Network-thread (%s) got error: %s of type: %s, socket_to_request was: %s" % (self.type, e, type(e), self.network.t_out.socket_to_request ) )

    def add_in_socket(self, client_socket):
        self.sockets_in.append(client_socket)
        
    def add_out_socket(self, client_socket):
        with self.socket_to_request_lock:
            self.socket_to_request[client_socket] = []
            
        self.sockets_out.append(client_socket)
    
    def close_all_sockets(self):        
        for s in self.sockets_in + self.sockets_out:            
            try:
                #s.shutdown(0)   # Further receives are disallowed
                #s.shutdown(1)   # Further sends are disallowed.
                #s.shutdown(2)   # Further sends and receives are disallowed.
                s.close()                
            except Exception, e:
                Logger().error("Got error when closing socket: %s" % e)

    def _handle_readlist(self, readlist):
        #Logger().debug("Network-thread (%s) handling readlist for readlist: %s" % (self.type, readlist) )
        testCounter = 0
        for read_socket in readlist:
            add_to_pool = False
            try:
                # _ is sender_address
                (conn, _) = read_socket.accept()
                
                self.network.t_in.add_in_socket(conn)
                self.network.t_out.add_out_socket(conn)
                add_to_pool = True                
                #Logger().debug("Accepted connection on the main socket testCounter:%i" % testCounter)
                #if testCounter != 0:
                #    #if (read_socket == self.sockets_in[0])
                #    Logger().error("WOW, look at that counter ... just look at it!!! (%i) ... %s" % (testCounter,(read_socket == self.sockets_in[0]) ))
            except socket.error, e:
                # We try to accept on all sockets, even ones that are already in use.
                # This means that if accept fails it is normally just data coming in
                #Logger().debug("accept() threw: %s for socket:%s" % (e,read_socket) )
                conn = read_socket
            except Exception, e:
                Logger().error("_handle_readlist: Unknown error. Error was: %s" % e)
            
            try:
                rank, msg_command, raw_data = get_raw_message(conn)
                #Logger().debug("Found rank %d and command %s" % (rank, msg_command))
            except MPIException, e:                    
                # Broken connection is ok when shutdown is going on
                if self.shutdown_event.is_set():
                    #Logger().debug("_handle_readlist: get_raw_message threw: %s during shutdown" % e)
                    break # We don't care about incoming during shutdown
                else:
                    # We have no way of knowing whether other party has reached shutdown or this was indeed an error
                    # so we just try listening to next socket
                    #Logger().debug("_handle_readlist: Broken connection or worse. Error was: %s" % e)
                    continue
            except Exception, e:
                Logger().error("_handle_readlist: Unexpected error thrown from get_raw_message. Error was: %s" % e)
                continue
            
            # Now that we know the rank of sender we can add the socket to the pool
            if add_to_pool:
                self.network.socket_pool.add_accepted_socket(conn, rank)
            
            #Logger().debug("Received message with command: %d" % msg_command)
            if msg_command == constants.CMD_USER:
                try:
                    with self.network.mpi.raw_data_lock:
                        #Logger().debug("Got lock")
                        self.network.mpi.raw_data_queue.append(raw_data)
                        self.network.mpi.raw_data_has_work.set()
                        self.network.mpi.has_work_event.set()
                        #Logger().debug("Releasing lock")
                except AttributeError, e:
                    #Logger().error("Failed grabbing raw_data_lock!")
                    pass
                except Exception, e:
                    Logger().error("Strange error - Failed grabbing raw_data_lock!")
                    
            else:
                self.network.mpi.handle_system_message(rank, msg_command, raw_data)
            testCounter += 1
         
    def _handle_writelist(self, writelist):
        for write_socket in writelist:
            removal = []
            with self.socket_to_request_lock:
                request_list = self.socket_to_request[write_socket]
            for request in request_list:
                if request.status == "cancelled":
                    removal.append((socket, request))
                elif request.status == "new":                        
                    #Logger().debug("Starting data-send on %s. request: %s" % (write_socket, request))
                    # Send the data on the socket
                    try:
                        utils.robust_send(write_socket,request.data)
                    except socket.error, e:
                        #Logger().error("send() threw:%s for socket:%s with data:%s" % (e,write_socket,request.data ) )
                        # Send went wrong, do not update, but hope for better luck next time
                        continue
                    except Exception, e:
                        #Logger().error("Other exception robust_send() threw:%s for socket:%s with data:%s" % (e,write_socket,request.data ) )
                        # Send went wrong, do not update, but hope for better luck next time
                        continue
                    
                    removal.append((write_socket, request))
                    
                    if request.acknowledge:
                        request.update("unacked") # update status to wait for acknowledgement
                        #Logger().debug("Ssend done, status set to unacked")
                    else:                            
                        request.update("ready") # update status and signal anyone waiting on this request                            
                else:
                    pass
                    #Logger().warning("The socket select found an invalid request status: %s, type (%s), tag(%s) participant(%d)" % 
                    #        (request.status, request.request_type, request.tag, request.participant))
                    
            # Remove the requests (messages) that was successfully sent from the list for that socket
            if removal:
                removed = len(removal)
                with self.socket_to_request_lock:                
                    for (write_socket,matched_request) in removal:
                        self.socket_to_request[write_socket].remove(matched_request)
                    
                    self.outbound_requests -= removed

    def run(self):
        # TODO: Consider differentiating here for dual network threads
        
        # Main loop
        while not self.shutdown_event.is_set():
            # _ is errorlist
            (in_list, out_list, _) = self.select()
            self._handle_readlist(in_list)
            
            # Only look at outbound if there are any
            # (we don't take the socket_to_request_lock but worst case is we
            # might miss a send or handle_writelist once too much, which is ok)
            if self.outbound_requests > 0:
                self._handle_writelist(out_list)
        
        # The shutdown events is called, so we're finishing the network. This means
        # flushing all the send jobs we have and then closing the sockets.
        while self.socket_to_request:
            # _ is errorlist
            (in_list, out_list, _) = self.select()
            self._handle_writelist(out_list)

            removal = []
            for wsocket in self.socket_to_request:
                if not self.socket_to_request[wsocket]:
                    removal.append(wsocket)
            
            for r in removal:
                del self.socket_to_request[r]

class CommunicationHandlerEpoll(BaseCommunicationHandler):
    def __init__(self, *args, **kwargs):
        super(CommunicationHandlerEpoll, self).__init__(*args, **kwargs)
        
        # Add a special epoll environment we can later use to poll
        # the system. 
        self.epoll = select.epoll()

        self.in_fd_to_socket = {}
        self.out_fd_to_socket = {}

    def add_in_socket(self, client_socket):
        super(CommunicationHandlerEpoll, self).add_in_socket(client_socket)
        self.in_fd_to_socket[client_socket.fileno()] = client_socket
        self.epoll.register(client_socket, select.EPOLLIN)

    def add_out_socket(self, client_socket):
        super(CommunicationHandlerEpoll, self).add_out_socket(client_socket)
        self.out_fd_to_socket[client_socket.fileno()] = client_socket
        self.epoll.register(client_socket, select.EPOLLOUT)

    def select(self):
        in_list = []
        out_list = []
        error_list = []
        
        events = self.epoll.poll(1)
        for fileno, event in events:    
            if event & select.EPOLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))
            if event & select.EPOLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return (in_list, out_list, error_list)

class CommunicationHandlerPoll(BaseCommunicationHandler):
    def __init__(self, *args, **kwargs):
        super(CommunicationHandlerPoll, self).__init__(*args, **kwargs)
        
        # Add a special epoll environment we can later use to poll
        # the system. 
        self.poll = select.poll()

        self.in_fd_to_socket = {}
        self.out_fd_to_socket = {}

    def add_in_socket(self, client_socket):
        super(CommunicationHandlerPoll, self).add_in_socket(client_socket)
        self.in_fd_to_socket[client_socket.fileno()] = client_socket
        self.poll.register(client_socket, select.POLLIN)

    def add_out_socket(self, client_socket):
        super(CommunicationHandlerPoll, self).add_out_socket(client_socket)
        self.out_fd_to_socket[client_socket.fileno()] = client_socket
        self.poll.register(client_socket, select.POLLOUT)

    def select(self):
        in_list = []
        out_list = []
        error_list = []
        
        events = self.poll.poll(1)
        for fileno, event in events:    
            if event & select.POLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))
            if event & select.POLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return (in_list, out_list, error_list)

class CommunicationHandlerKqueue(BaseCommunicationHandler):
    def __init__(self, *args, **kwargs):
        super(CommunicationHandlerKqueue, self).__init__(*args, **kwargs)
        
        # Add a special kqueue environment we can later use to poll
        # the system. 
        self.kqueue_changelist_lock = threading.Lock()
        self.kqueue_changelist = []            # I think this needs to go away.
        self.kqueue = select.kqueue()
        self.in_ident_to_socket = {}
        self.out_ident_to_socket = {}

    def add_in_socket(self, client_socket):
        super(CommunicationHandlerKqueue, self).add_in_socket(client_socket)
        self.in_ident_to_socket[client_socket.fileno()] = client_socket
        event = select.kevent(client_socket, filter=select.KQ_FILTER_READ, flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE)
        self.kqueue_changelist.append(event)
        
    def add_out_socket(self, client_socket):
        super(CommunicationHandlerKqueue, self).add_out_socket(client_socket)
        self.out_ident_to_socket[client_socket.fileno()] = client_socket
        event = select.kevent(client_socket, filter=select.KQ_FILTER_WRITE, flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE)
        self.kqueue_changelist.append(event)
        Logger().debug("Adding <ident,socket> pair to internal structure <%s,%s>" % (event.ident, client_socket))

    def select(self):
        in_list = []
        out_list = []
        error_list = []
        
        with self.kqueue_changelist_lock:

            events = []
            for kevent in self.kqueue_changelist: 
                new_events = self.kqueue.control([kevent], 10, 0)
                events.extend(new_events)
                
            new_events = self.kqueue.control(None, 10, 0)
            events.extend(new_events)
            
            for event in events:
                if event.filter == select.KQ_FILTER_READ:
                    Logger().warning("--------------> read: event ident %s and flag %s" % (event.ident, event.flags))

                    socket = self.in_ident_to_socket.get(event.ident, None)
                    if socket:
                        in_list.append(socket)
                    else:
                        Logger().warning("read: Throwing socket away for event ident %s, filter %s and flag %s" % (event.ident, event.filter, event.flags))
                        
                elif event.filter == select.KQ_FILTER_WRITE:
                    socket = self.out_ident_to_socket.get(event.ident, None)
                    if socket:
                        out_list.append(socket)
                    else:
                        Logger().warning("write: Throwing socket away for event ident %s and flag %s" % (event.ident, event.flags))
                else:
                    Logger.warning("==============> unknown event ident %s, filter %s and flag %s" % (event.ident, event.filter, event.flags))
                    if event.flags == select.KQ_EV_ERROR:
                        Logger().warning("Error detected in kqueue control call. ")
                        Logger().warning("We received an event with identifier (%s), filter (%s), flags (%s) fflags (%s) udata(%s)" % (event.ident, event.filter, event.flags, event.fflags, event.udata))
                    
            # Reset the change list
            self.kqueue_changelist = []
            
        return (in_list, out_list, error_list)
        
class CommunicationHandlerSelect(BaseCommunicationHandler):
    """
    This is a single thread doing both in and out or there are two threaded instances one for each
    """
    def select(self):
        try:
            return select.select( self.sockets_in, self.sockets_out, self.sockets_in + self.sockets_out, 1)
        except Exception, e:
            Logger().error("Network-thread (%s) Got exception: %s of type: %s" % (self.type, e, type(e)) )

