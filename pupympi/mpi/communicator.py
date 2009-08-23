# Fred dabbling in communication
from mpi.exceptions import MPINoSuchRankException
from mpi.logger import Logger
import threading
from mpi.request import Request

class Communicator:
    """
    This class represents a communicator.
    """
    def __init__(self, rank, size, network, name="MPI_COMM_WORLD"):
        self._rank = rank
        self._size = size
        self.name = name
        self.members = {}
        self.network = network


        self.attr = {}
        if name == "MPI_COMM_WORLD":
            self.attr = {   "MPI_TAG_UB": 2**30, \
                            "MPI_HOST": "TODO", \
                            "MPI_IO": rank, \
                            "MPI_WTIME_IS_GLOBAL": False
                        }

        # Addind locks and initial information about the request queue
        self.current_request_id_lock = threading.Lock()
        self.request_queue_lock = threading.Lock()
        self.current_request_id = 0
        self.request_queue = {}
    
    def build_world(self, all_procs):
        self.members = all_procs

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

    def update(self):
        """
        This method is responsible for listening on the TCP layer, receive
        information on network requests and update the internal Requests 
        objects that live in the request_queue.

        FIXME: We need to have access to the network layer and receive all
        the finished tasks for this communicator. We can then update the 
        request status.
        """
        logger = Logger()
        logger.debug("Update by the mpi thread in communicator: %s" % self.name)

        # Loook through all the request objects to see if there is anything we can do here
        for request in self.request_queue.values():
            # We will skip requests objects that are not possible to
            # acquire a lock on right away. 
            if not request.acquire(False):
                continue

            status = request.get_status()

            # Just switch on the different status something can have
            if status == 'cancelled':
                # We remove the cancelled request, but I think we might need to
                # cache it. What if there is a subsequent isend/irecv starting 
                # receiving the data ment for this one. (the data might already
                # be here)
                self.request_remove( request )
                Logger().info("Removing cancelled request")

            elif status == 'ready':
                # Ready means that we're waiting for the user to do something about
                # it. We can't do anything.
                continue

            elif status == 'finished':
                # All done, so it should be safe to remove. We're seperating this
                # request from the cancelled so it's easier to make different in 
                # the future
                self.request_remove( request )
                Logger().info("Removing finished request")
        
            elif status == 'new':
                if request.type == "receive":
                    # We ask the network layer if there are any messages from 
                    # our recipient, with our data in our communicator. If so
                    # we update the request object so the wait() can finish. 
                    data = self.network.get_received_data(request.participant, request.tag, self)
                    if data:
                        Logger().info("Found data from the nework ready to update a request object")
                        request.update(status='ready', data=data, lock=False)
            else:
                logger.warning("Updating the request queue in communicator %s got a unknown status: %s" % (self.name, status))

            # Release the lock after we're done
            request.release()

    def request_remove(self, request_obj):
        self.request_queue_lock.acquire()
        del self.request_queue[request_obj.queue_idx]
        self.request_queue_lock.release()

    def request_add(self, request_obj):
        """
        Add the request object to a queue so we can get a hold of it later.
        Returns the lookup idx for later use.
        """
        logger = Logger()
        logger.debug("Adding request object to the request queue")
        self.current_request_id_lock.acquire()
        self.current_request_id += 1
        idx = self.current_request_id
        self.current_request_id_lock.release()

        # Set the id on the request object so we can read it directly later
        request_obj.queue_idx = idx

        self.request_queue_lock.acquire()
        self.request_queue[idx] = request_obj
        self.request_queue_lock.release()
        logger.debug("Added request object to the queue with index %s. There are now %d items in the queue" % (idx, len(self.request_queue)))
        return idx

    def have_rank(self, rank):
        return rank in self.members
    
    def get_network_details(self, rank):
        if not self.have_rank(rank):
            raise MPINoSuchRankException()

        return self.members[rank]
    
    def rank(self):
        return self._rank

    def size(self):
        return self._size

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def irecv(self, sender, tag):
        # Check the destination exists
        if not self.have_rank(sender):
            raise MPINoSuchRankException("No process with rank %d in communicator %s. " % (sender, self.name))

        # Create a receive request object and return
        handle = Request("receive", self, sender, tag)

        # Add to the queue
        self.request_add(handle)
        return handle

    def isend(self, destination_rank, content, tag):
        logger = Logger()
        # Check the destination exists
        if not self.have_rank(destination_rank):
            raise MPINoSuchRankException("Not process with rank %d in communicator %s. " % (destination_rank, self.name))

        # Create a receive request object and return
        handle = Request("send", self, destination_rank, tag, data=content)

        # Add to the queue
        self.request_add(handle)
        return handle

    # TODO: may want to drop this and simply allow users access to the underlying dict?
    # TODO: Global fixed keys (http://www.mpi-forum.org/docs/mpi-11-html/node143.html) should be defined?
    def attr_get(self, key):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html, python-style:
        keyval is now any immutable datatype, and flag is not used. If the key is not defined, None is returned. """
        return self.attr[key]
    def attr_put(self, key, value):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html"""
        self.attr[key] = value   
        

    ################################################################################################################
    # NETWORK OPERATIONS
    ################################################################################################################
    
    # deliberately skipped:
    # 
    # due to having to do with data types or memory management:
    # mpi_address,
    # mpi_buffer_attach, mpi_buffer_detach
    # pack, pack_size
    #
    # due to making no sense in a python environment:
    # bsend, ibsend
    # rsend, irsend
    # 
    # due to having to do with error handling: 
    # mpi_error_*
    # 
    # due to user defined functions:
    # mpi_op_create/free
    # 
    # due to being about inter communicators:
    # mpi_comm_remote_group/size, mpi_intercomm_create/merge
    #
    # due to being related to profiling:
    # mpi_pcontrol
    # 
    # other stuff, related to requests that may get done:
    # MPI TEST, 43 
    # MPI TEST CANCELLED, 55 
    # MPI TESTALL, 48 
    # MPI TESTANY, 47 
    # MPI TESTSOME, 50 
    # MPI TOPO TEST, 184 
    # MPI WAIT, 42 
    # MPI WAITALL, 48 
    # MPI WAITANY, 46 
    # MPI WAITSOME, 49 
    # MPI WTICK, 201 
    # MPI_TYPE_CREATE_DARRAY (Distributed Array Datatype Constructor)


    # Some wrapper methods
    def send(self, destination, content, tag):
        """
        document me
        """
        return self.isend(destination, content, tag).wait()

    def barrier(self):
        """
        document me
        """
        Logger().warn("Non-Implemented method 'Barrier' called.")
        # FIXME: Insert something on the request queue

    def recv(self, destination, tag):
        """
        document me
        """
        return self.irecv(destination, tag).wait()

    def abort(self, arg):
        """
        This routine makes a "best attempt" to abort all tasks in the group of comm.
        http://www.mpi-forum.org/docs/mpi-11-html/node151.html
            // Example C code
            #include <mpi.h>
            int main(int argc, char *argv[])
            {
                MPI_Init(NULL, NULL);
                MPI_Abort(MPI_COMM_WORLD, 911);
                /* No further code will execute */
                MPI_Finalize();
                return 0;
            }
        """
        Logger().warn("Non-Implemented method 'abort' called.")

    def allgather(self, sendbuf, sendcount, recvcount):
        """
        MPI_ALLGATHER can be thought of as MPI_GATHER, but where all processes receive the result, instead of just the root. 
        The block of data sent from the jth process is received by every process and placed in the jth block of the buffer recvbuf. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node73.html#Node73
        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allgather.html        
        """
        # TODO return recvbuf
        Logger().warn("Non-Implemented method 'allgather' called.")

    def allgatherv(self, sendbuf, sendcount, recvcount, displs):
        """
        MPI_ALLGATHERV can be thought of as MPI_GATHERV, but where all processes receive the result, instead of just the root. The  jth block of data sent from each process is received by every process and placed in the  jth block of the buffer recvbuf. These blocks need not all be the same size. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node73.html#Node73
        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allgatherv.html        
        """
        # TODO return recvbuf
        Logger().warn("Non-Implemented method 'allgatherv' called.")

    def allreduce(self, sendbuf, recvbuf, count, op):
        """
        Same as MPI_REDUCE except that the result appears in the receive buffer of all the group members.

        http://www.mpi-forum.org/docs/mpi-11-html/node82.html        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allreduce.html
        """
        Logger().warn("Non-Implemented method 'allreduce' called.")
        
    def alltoall(self, sendbuf, sendcount, recvbuf, recvcount):
        """
        IN sendbuf starting address of send buffer (choice) 
        IN sendcount number of elements sent to each process (integer) 
        IN recvcount number of elements received from any process (integer) 
        IN comm communicator (handle) 
        OUT recvbuf address of receive buffer (choice) 
        
        MPI ALLTOALL is an extension of MPI ALLGATHER to the case where each process 
        sends distinct data to each of the receivers. The jth block sent from process i is received 
        by process j and is placed in the ith block of recvbuf...
        
        http://www.mpi-forum.org/docs/mpi-11-html/node75.html
        Example: http://mpi.deino.net/mpi_functions/MPI_Alltoall.html
        """

        Logger().warn("Non-Implemented method 'alltoall' called.")
        
    def alltoallv(self, sendbuf, sendcount, sdispls, recvbuf, recvcount, rdispls):
        """
        IN sendbuf starting address of send buffer (choice) 
        IN sendcounts integer array equal to the group size specifying the number of elements to send to each processor 
        IN sdispls integer array (of length group size). Entry j specifies the displacement (relative to sendbuf from which to take the outgoing data destined for process j 
        IN sendtype data type of send buffer elements (handle) 
        OUT recvbuf address of receive buffer (choice) 
        IN recvcounts integer array equal to the group size specifying the number of elements that can be received from each processor 
        IN rdispls integer array (of length group size). Entry i specifies the displacement (relative to recvbuf at which to place the incoming data from process i) 
        
        MPI_ALLTOALLV adds flexibility to MPI_ALLTOALL in that the location of data for the send is specified by sdispls
        and the location of the placement of the data on the receive side is specified by rdispls. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node75.html    
        """
        
        Logger().warn("Non-Implemented method 'alltoallv' called.")
        
    def bcast(self, buffer, count, root):
        """
        INOUT buffer starting address of buffer (choice) 
        IN count number of entries in buffer (integer) 
        IN datatype data type of buffer (handle) 
        IN root rank of broadcast root (integer) 
        IN comm communicator (handle) 

        MPI BCAST broadcasts a message from the process with rank root to all processes of 
        the group, itself included. It is called by all members of group using the same arguments 
        or comm, root. On return, the contents of root's communication buffer has been copied to all processes. 

        http://www.mpi-forum.org/docs/mpi-11-html/node67.html
        """
    
        Logger().warn("Non-Implemented method 'bcast' called.")
        
    def gather(self, sendbuf, sendcount, recvbuf, recvcount, root):
        """
        Each process (root process included) sends the contents of its send buffer to the root 
        process. The root process receives the messages and stores them in rank order. 
        
        IN sendbuf starting address of send buffer (choice) 
        IN sendcount number of elements in send buffer (integer) 
        IN sendtype data type of send buffer elements (handle) 
        OUT recvbuf address of receive buffer (choice, significant only at root) 
        IN recvcount number of elements for any single receive (integer, significant only at root) 
        IN recvtype data type of recv buffer elements (significant only at root) (handle) 
        IN root rank of receiving process (integer) 
        IN comm communicator (handle) 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node69.html
        """
        Logger().warn("Non-Implemented method 'gather' called.")
        
    def gatherv(self, sendbuf, sendcount, recvbuf, recvcount, displs, root):
        """
        MPI GATHERV extends the functionality of MPI GATHER by allowing a varying count 
        of data from each process, since recvcounts is now an array. It also allows more flexibility 
        as to where the data is placed on the root, by providing the new argument, displs. 

        IN sendbuf starting address of send buffer (choice) 
        IN sendcount number of elements in send buffer (integer) 
        IN sendtype data type of send buffer elements (handle) 
        OUT recvbuf address of receive buffer (choice, significant only at root) 
        IN recvcount number of elements for any single receive (integer, significant only at root) 
        IN recvtype data type of recv buffer elements (significant only at root) (handle) 
        IN displs integer array (of length group size). Entry i specifies the displacement relative to recvbuf at which to place 
        the incoming data from process i (significant only at root) 
        
        IN root rank of receiving process (integer) 
        IN comm communicator (handle) 

        http://www.mpi-forum.org/docs/mpi-11-html/node69.html
        """
        Logger().warn("Non-Implemented method 'gatherv' called.")
        
    # FIXME Defer/discuss whether to implement these (probes for incoming receives)
    def probe(self, arg):
        # TODO Document
        pass
    def iprobe(self, arg):
        # TODO Document
        pass
        
    def reduce(self, arg):
        # FIXME
        pass
    
    def reduce_scatter(self, arg):
        # FIXME
        pass
        
    def scan(self, arg):
        # FIXME
        pass
        
    def scatter(self, arg):
        # FIXME
        pass
        
    def scatterv(self, arg):
        # FIXME
        pass
    
    def start(self, arg):
        # TODO The argument, request, is a handle returned by one of the
        # previous five  calls. The ass. request should be inactive. The
        # request becomes active once the call is made.
        pass
    
    def startall(self, arg):
        # TODO The argument, request, is a handle returned by one of the
        # previous five  calls. The ass. request should be inactive. The
        # request becomes active once the call is made.
        pass
        
    def mname(self, arg):
        pass

    ################################################################################################################
    # LOCAL OPERATIONS
    ################################################################################################################
    
    #### Inter-communicator operations
    # TODO Need to officially decide if inter-communicators are implemented and if not, why (imo: not to be implemented.) 
    def test_inter(self):
        """
        This local routine allows the calling process to determine if a communicator is an inter-communicator or an intra-communicator. It returns true if it is an inter-communicator, otherwise false. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node112.html
        """
        return False
