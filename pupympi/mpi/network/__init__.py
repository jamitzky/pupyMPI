#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
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

from mpi.exceptions import MPIException
from mpi.network.socketpool import SocketPool
from mpi.network import utils # Some would like the rest of the utils to be more explicitly used ... maybe later
from mpi.network.utils import create_random_socket, get_raw_message, prepare_message, pickle
from mpi import constants, syscommands
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
            #Logger().debug("Socket Pool DYNAMIC size:%i" % socket_pool_size)
        else:
            # We need extra room for an admin connection.
            socket_pool_size = options.size+1

        self.socket_pool = SocketPool(socket_pool_size)

        communicator_class = get_communicator_class(options.socket_poll_method)

        self.mpi = mpi
        self.options = options
        self.t_in = communicator_class(self, options.rank, self.socket_pool)
        self.t_in.daemon = True
        self.t_in.name = "Comms Rx"
        self.t_in.start()

        if options.single_communication_thread:
            self.t_out = self.t_in
            self.t_out.type = "combo"
            self.t_out.name = "Comms"
        else:
            self.t_out = communicator_class(self, options.rank, self.socket_pool)
            self.t_out.name = "Comms Tx"
            self.t_out.daemon = True
            self.t_out.start()
            self.t_out.type = "out"
            self.t_in.type = "in"

        # Create the main receieve socket
        (server_socket, hostname, port_no) = create_random_socket()
        self.port = port_no
        self.hostname = hostname
        server_socket.listen(5)
        #self.main_receive_socket = server_socket
        # Put main receieve socket on incoming list
        self.t_in.add_in_socket(server_socket)
        #self.t_in.add_in_socket(self.main_receive_socket)

        # Set main receive socket for comparison in _handle_readlist
        self.t_in.main_receive_socket = server_socket

        #Logger().debug("--starting handshake, main socket is: %s" % server_socket)

        # Do the initial handshaking with the other processes
        self._handshake(options.mpi_conn_host, int(options.mpi_conn_port), int(options.rank))

        self.full_network_startup = not options.disable_full_network_startup

        #Logger().debug("Network initialized")
        #global done
        #done = False

    def _handshake(self, mpirun_hostname, mpirun_port, internal_rank):
        """
        This method creates the MPI_COMM_WORLD communicator, by receiving
        (hostname, port, rank) for all the processes started by mpirun.

        For mpirun to have this information we first send all the data
        from our own process. So we can bind a socket.

        The data sent back to mpirun.py is a tuple containing the following
        elements:

            * hostname           : Our hostname
            * port               : Our port number. Together with hostname, this
                                   information makes it possible to connect with
                                   this instance.
            * rank               : Our rank. The mpirun.py process will distribute
                                   this information among the other processes.
            * security_component : A SHA1 hash used for "security". Scripts
                                   communicating with the MPI environment must
                                   supply this as a simple way to disallow
                                   other than the starting user.
            * availability       : Information about each system commands
                                   availability on this host.
        """
        sec_comp = self.mpi.generate_security_component()
        avail = syscommands.availablity()

        # Packing the data
        data = (self.hostname, self.port, internal_rank, sec_comp, avail)

        # Connection to the mpirun processs
        s_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recipient = (mpirun_hostname, mpirun_port)
        s_conn.connect(recipient)

        # Pack the data with our special format
        utils.robust_send(s_conn, prepare_message(data, internal_rank, comm_id=-1, tag=constants.TAG_INITIALIZING))

        # Receiving data about the communicator, by unpacking the head etc.
        # first _ is rank
        _, _, _, _, _, all_procs = get_raw_message(s_conn)
        all_procs = pickle.loads(all_procs)

        s_conn.close()

        self.all_procs = {}

        for (host, port, global_rank) in all_procs:
            self.all_procs[global_rank] = {'host' : host, 'port' : port, 'global_rank' : global_rank}

    def start_full_network(self):
        # We make a full network startup by receiving from all with lower ranks and
        # sending to higher ranks
        our_rank = self.mpi.MPI_COMM_WORLD.rank()
        size = self.mpi.MPI_COMM_WORLD.size()

        receiver_ranks = [x for x in range(0, our_rank)]
        sender_ranks = range(our_rank+1, size)

        recv_handles = []
        # Start all the receive
        for r_rank in receiver_ranks:
            handle = self.mpi.MPI_COMM_WORLD.irecv(r_rank, constants.TAG_FULL_NETWORK)
            recv_handles.append(handle)

        # Send all
        for s_rank in sender_ranks:
            self.mpi.MPI_COMM_WORLD._send(our_rank, s_rank, constants.TAG_FULL_NETWORK)

        # Finish the receives
        for handle in recv_handles:
            handle.wait()

        # Full network start up means a static socket pool
        self.socket_pool.readonly = True

    def _direct_send(self, communicator, message="", receivers=[], tag=constants.MPI_TAG_ANY):
        from mpi.request import Request
        rl = []
        message = pickle.dumps(message)
        for recp in receivers:
            request = Request("send", communicator, recp, tag, data=message)
            request.is_pickled = True
            self.t_out.add_out_request(request)
            rl.append(request)

        return rl

    def finalize(self):
        """
        Forwarding the finalize call to the threads. Look at the
        CommunicationHandlerSelect.finalize for a deeper description of
        the shutdown procedure.
        """
        self.t_in.finalize()

        if not self.options.single_communication_thread:
            self.t_out.finalize()

        # Wait for network threads to die
        self.t_in.join()
        self.t_out.join()

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
        self.main_receive_socket = None # For threads handling incoming this is the main socket on which new connections can be accepted

        self.shutdown_event = threading.Event() # signal for shutdown
        #self.outbound_requests_event = threading.Event() # signal for something to send

        # Locks for proper access to the internal socket->request structure and counter
        self.socket_to_request_lock = threading.Lock()

        self.debug_counter = 0

    def get_state(self):
        return {
            'type' : self.type,
            'debug_counter' : self.debug_counter,
            'rank' : self.rank,
        }

    def finalize(self):
        self.shutdown_event.set()

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
        request.data = prepare_message(request.data, request.communicator.rank(), cmd=request.cmd,
                                       tag=request.tag, ack=request.acknowledge, comm_id=request.communicator.id, is_pickled=request.is_pickled)

        # TODO: This call should be extended to allow asking for a persistent connection
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
                s.close()
            except Exception, e:
                Logger().error("Got error when closing socket: %s" % e)

    def _handle_readlist(self, readlist):

        for read_socket in readlist:
            add_to_pool = False

            if read_socket == self.main_receive_socket:
                try:
                    # _ is sender_address
                    (conn, _) = read_socket.accept()

                    self.network.t_in.add_in_socket(conn)
                    self.network.t_out.add_out_socket(conn)
                    add_to_pool = True
                except socket.error, e:
                    # We try to accept but if accept fails maybe it just data coming in?
                    Logger().error("accept() threw: %s on the main recv socket:%s" % (e,read_socket) )
                except Exception, e:
                    Logger().error("_handle_readlist: Unknown error. Error was: %s" % e)
            else:
                conn = read_socket

            try:
                rank, msg_command, tag, ack, comm_id, raw_data = get_raw_message(conn)
            except MPIException, e:
                # Broken connection is ok when shutdown is going on
                if self.shutdown_event.is_set():
                    break # We don't care about incoming during shutdown
                else:
                    # We have no way of knowing whether other party has reached shutdown or this was indeed an error
                    # so we just try listening to next socket
                    continue
            except Exception, e:
                Logger().error("_handle_readlist: Unexpected error thrown from get_raw_message. Error was: %s" % e)
                continue

            # Now that we know the rank of sender we can add the socket to the pool
            if add_to_pool:
                self.network.socket_pool.add_accepted_socket(conn, rank)

            if msg_command == constants.CMD_USER:
                try:
                    with self.network.mpi.raw_data_lock:
                        self.network.mpi.raw_data_queue.append( (rank, tag, ack, comm_id, raw_data))
                        self.network.mpi.raw_data_has_work.set()
                        self.network.mpi.has_work_event.set()
                except AttributeError, e:
                    pass
                except Exception, e:
                    Logger().error("Strange error - Failed grabbing raw_data_lock!")
            else:
                self.network.mpi.handle_system_message(rank, msg_command, raw_data, conn)

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

            # Remove the requests (messages) that was successfully sent from the list for that socket
            if removal:
                removed = len(removal)
                with self.socket_to_request_lock:
                    for (write_socket,matched_request) in removal:
                        self.socket_to_request[write_socket].remove(matched_request)

                    self.outbound_requests -= removed

    def run(self):
        # DEBUG
        emptyreads = 0
        emptywrites = 0

        # Stall until network thread type is set
        # TODO: This hack should be refactored.
        while not self.type in ("combo","in","out"):
            time.sleep(0.001)

        if self.type == "combo":

            # Main loop
            while not self.shutdown_event.is_set():
                # _ is errorlist
                (in_list, out_list, _) = self.select_combo()
                self._handle_readlist(in_list)

                # Only look at outbound if there are any
                # (we don't take the socket_to_request_lock but worst case is we
                # might miss postpone a send for one iteration or handle_writelist
                # once too much, both are acceptable compared to locking)
                if self.outbound_requests > 0:
                    self._handle_writelist(out_list)


                # NOTE:
                # This microsleep is to avoid busy waiting which starves the other threads
                # especially on a single node (localhost testing) this has significant effect
                # but also on the cluster it halves the time required for the single module!
                # And furthermore increases max transferrate by 25% to about 40MB/s!
                # Also it seems to improve the speed of high computation-to-communication like
                # in the Monte Carlo Pi application where 20% speed has been observed
                time.sleep(0.00001)

        elif self.type == "in":
            #Logger().debug("- - in")
            while not self.shutdown_event.is_set():
                #Logger().debug("Select in - for base communication handler type:%s" %(self.type))
                (in_list, _, _) = self.select_in()

                #DEBUG
                if not in_list:
                    emptyreads += 1

                self._handle_readlist(in_list)
                time.sleep(0.00001)

        elif self.type == "out":
            #Logger().debug("- - out")
            while not self.shutdown_event.is_set():
                if self.outbound_requests > 0:
                    (_, out_list, _) = self.select_out()
                    #DEBUG
                    if not out_list:
                        emptywrites += 1
                    self._handle_writelist(out_list)

                time.sleep(0.00001)


        # The shutdown events is called, so we're finishing the network. This means
        # flushing all the send jobs we have and then closing the sockets.
        if self.type in ("combo","out"):
            while self.socket_to_request:
                (_, out_list, _) = self.select_out()
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
        self.epoll.register(client_socket, select.EPOLLIN) # Default mode is level triggered
        #self.epoll.register(client_socket, select.EPOLLIN | select.EPOLLET) # Edge triggered

    def add_out_socket(self, client_socket):
        super(CommunicationHandlerEpoll, self).add_out_socket(client_socket)
        self.out_fd_to_socket[client_socket.fileno()] = client_socket
        self.epoll.register(client_socket, select.EPOLLOUT)

    def select_combo(self):
        in_list = []
        out_list = []
        error_list = []

        events = self.epoll.poll(1)
        #events = self.epoll.poll()
        for fileno, event in events:
            if event & select.EPOLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))
            if event & select.EPOLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return (in_list, out_list, error_list)

    def select_in(self):
        in_list = []
        error_list = []

        events = self.epoll.poll(0.001)
        for fileno, event in events:
            if event & select.EPOLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))

        return (in_list, [], error_list)

    def select_out(self):
        out_list = []
        error_list = []

        #events = self.epoll.poll(1)
        events = self.epoll.poll()
        for fileno, event in events:
            if event & select.EPOLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return ([], out_list, error_list)


class CommunicationHandlerPoll(BaseCommunicationHandler):
    def __init__(self, *args, **kwargs):
        super(CommunicationHandlerPoll, self).__init__(*args, **kwargs)

        # Add a special poll environment we can later use to poll
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

    def select_combo(self):
        in_list = []
        out_list = []
        error_list = []

        events = self.poll.poll(0.00001)
        #events = self.poll.poll()
        for fileno, event in events:
            if event & select.POLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))
            if event & select.POLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return (in_list, out_list, error_list)

    def select_in(self):
        in_list = []
        error_list = []

        events = self.poll.poll(0.00001)
        for fileno, event in events:
            if event & select.POLLIN:
                in_list.append(self.in_fd_to_socket.get(fileno))

        return (in_list, [], error_list)

    def select_out(self):
        out_list = []
        error_list = []

        #events = self.poll.poll(1)
        events = self.poll.poll()
        for fileno, event in events:
            if event & select.POLLOUT:
                out_list.append(self.out_fd_to_socket.get(fileno))

        return ([], out_list, error_list)

class CommunicationHandlerSelect(BaseCommunicationHandler):
    """
    This is a single thread doing both in and out or there are two threaded instances one for each
    """
    def select_combo(self):
        try:
            #return select.select( self.sockets_in, self.sockets_out, self.sockets_in + self.sockets_out)
            return select.select( self.sockets_in, self.sockets_out, self.sockets_in + self.sockets_out, 1)
        except Exception, e:
            Logger().error("Network-thread (%s) Got exception: %s of type: %s" % (self.type, e, type(e)) )

    def select_in(self):
        try:
            #return select.select( self.sockets_in, [], self.sockets_in)
            return select.select( self.sockets_in, [], self.sockets_in, 1)
        except Exception, e:
            Logger().error("Network-thread (%s) Got exception: %s of type: %s" % (self.type, e, type(e)) )

    def select_out(self):
        try:
            #return select.select( [], self.sockets_out, self.sockets_out)
            return select.select( [], self.sockets_out, self.sockets_out, 1)
        except Exception, e:
            Logger().error("Network-thread (%s) Got exception: %s of type: %s" % (self.type, e, type(e)) )
