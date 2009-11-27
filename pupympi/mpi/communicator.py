from mpi.exceptions import MPINoSuchRankException, MPIInvalidTagException, MPICommunicatorGroupNotSubsetOf,MPICommunicatorNoNewIdAvailable, MPIException
from mpi.logger import Logger
import threading,sys,copy,time
from mpi.request import Request
from mpi.bc_tree import BroadCastTree
from mpi.collectiverequest import CollectiveRequest
from mpi.group import Group
from mpi import constants

class Communicator:
    """
    This class represents an MPI communicator. The communicator holds information
    about a 'group' of processes and allows for inter communication between these. 

    It's not possible from within a communicator to talk with processes outside. Remember
    you have the MPI_COMM_WORLD communicator holding ALL the started proceses. 
    """
    def __init__(self, mpi, rank, size, network, group, id=0, name="MPI_COMM_WORLD", comm_root = None):
        self.mpi = mpi 
        self.name = name
        self.network = network
        self.comm_group = group
        self.id = id
        self.id_ceiling = sys.maxint # for local communicator creation, can be deleted otherwise.
        self.MPI_COMM_WORLD = comm_root or self
        
        self.mpi.communicators[self.id] = self # TODO bit of a side-effect here, by automatically registering on new
        
        self.attr = {}
        if name == "MPI_COMM_WORLD":
            self.attr = {   "MPI_TAG_UB": 2**30, \
                            "MPI_HOST": "TODO", \
                            "MPI_IO": rank, \
                            "MPI_WTIME_IS_GLOBAL": False
                        }


        # Setup a tree for this communicator. When this is done you can
        # use the "up" and "down" attributes on the tree to send messages
        # around. The standard tree is created with rank 0 as the root.
        # Look at the inner "get_broadcast_tree" to see how you can get
        # trees with different roots
        self.get_broadcast_tree()

    def get_broadcast_tree(self, root=0):
        # Ensure we have the tree structure
        if not getattr(self, "bc_trees", None):
            self.bc_trees = {}

        # Look for the root as key in the structure. If so we use this
        # tree as it has been generated earlier. This makes the system
        # act like a caching system, so we don't end up generating trees
        # all the time.
        if root not in self.bc_trees:
            self.bc_trees[root] = BroadCastTree(range(self.size()), self.rank(), root)
            self.bc_trees[root]
        
        return self.bc_trees[root] 
                
    def __repr__(self):
        return "<Communicator %s, id %s with %d members>" % (self.name, self.id, self.comm_group.size())

    def have_rank(self, rank):
        return rank in self.comm_group.members
    
    def get_network_details(self, rank):
        if not self.have_rank(rank):
            raise MPINoSuchRankException()

        return self.comm_group.members[rank]
    
    def rank(self):
        return self.comm_group.rank()

    def size(self):
        return self.comm_group.size()
        
    def group(self):
        """
        returns the group associated with a communicator 
        """
        return self.comm_group

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name
        
    ################################################################################################################
    #### Communicator creation, deletion
    ################################################################################################################
    def _comm_call_attrs(self, **kwargs):
        """Iterates through each value in the cached attribute collection and calls the value if its callable"""
        for a in self.attr: # FIXME not tested
            if hasattr(self.attr[a], '__call__'):
                Logger().debug("Calling callback function on '%s'" % a)                
                self.attr[a](self, **kwargs)
        # done
        
    def comm_create(self, group):
        """
        This function creates a new communicator newcomm with communication
        group defined by group and a new context. No cached information
        propagates from comm to newcomm. The function returns
        None to processes that are not in group.
        The call is erroneous if not all group arguments have the same value,
        or if group is not a subset of the group associated with comm.
        Note that the call is to be executed by all processes in comm,
        even if they do not belong to the new group.

        This call applies only to intra-communicators. 

        [ IN comm] communicator (handle - self object)
        [ IN group] Group, which is a subset of the group of comm
        [ OUT newcomm] new communicator

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node102.html

        .. note::This call is internally implemented either locally, in which case only 32 new communicators 
        can be created across the lifespan of your MPI application, or collective with no (realistic) limit on 
        the amount of created communicators but is significantly slower. 
        **FIXME** There is presently no way to determine which implementation is in effect. 
        """
        # check if group is a subset of this communicators' group
        for potential_new_member in group.members:
            if potential_new_member not in self.group().members:
                raise MPICommunicatorGroupNotSubsetOf(potential_new_member)

        #return self._comm_create_coll(group)        
        new_comm = self._comm_create_local(group)        
        return new_comm
    
    ceiling = sys.maxint
    def _comm_create_local(self, group):
        """
        local only implementation. Can only handle log2(sys.maxint)-1 (ie 31 or 32) communicator creation depth/breadth. 
        """
        
        # FIXME should probably lock...
        if self.ceiling <= 2:
            raise MPICommunicatorNoNewIdAvailable("Local communication creation mode only supports log2(sys.maxint)-1 creation depth, and you've exceeded that.")
        # set up some easily understandable vars (can be optimized later)
        old_comm_id = self.id
        old_comm_ceiling = self.ceiling
        
        new_comm_ceiling = old_comm_ceiling
        new_comm_id = ((new_comm_ceiling-old_comm_id)/2)+old_comm_id
        self.ceiling = new_comm_id
        newcomm = Communicator(self.mpi, group.rank(), group.size(), self.network, group, new_comm_id, name = "new_comm %s" % new_comm_id, comm_root = self.MPI_COMM_WORLD)
        newcomm.ceiling = new_comm_ceiling
        return newcomm

    def _comm_create_coll(self, group):
        """
        Collective implementation of the comm_create call
        """
        logger = Logger()
        
        new_id = -1

        if self.rank() == 0:
            # send request to rank 0 of mpi_comm_world (if already rank 0 of mcw, just send the message anyway)
            self.MPI_COMM_WORLD.send(self.MPI_COMM_WORLD.group().members[0], None, constants.TAG_COMM_CREATE)
            new_id = self.MPI_COMM_WORLD.recv(self.MPI_COMM_WORLD.group().members[0], constants.TAG_COMM_CREATE)

        if new_id < 0:
            raise MPICommunicatorNoNewIdAvailable("New valid communicator id was not distributed to whole group")
        
        # wait for answer on id
        cr = CollectiveRequest(constants.TAG_COMM_CREATE, self, new_id)
        
        # FIXME validate that received group was identical to my worldview

        # Non-members have rank -1
        if not group._owner_is_member():
            return None
            
        newcomm = Communicator(self.mpi, group.rank(), group.size(), self.network, group, new_id, name = "new_comm %s" % new_id, comm_root = self.MPI_COMM_WORLD)
        return newcomm

    def comm_free(self):
        """
        This operation marks the communicator object as closed. 
        
        .. note::
            *Deviation:* This method deviates from the MPI standard by not being collective, and by not actually deallocating the object itself.
        
        The delete callback functions for any attributes are called in arbitrary order.

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node103.html#Node103
        """
        self._comm_call_attrs(type = self.comm_free, calling_comm = self)                

        # thats it....dont do anything more. This deviates from the MPI standard.


    def comm_split(self, existing_communicator, color, key = None):
        """
        This function partitions the group associated with comm into disjoint subgroups, one for each value of color. 
        Each subgroup contains all processes of the same color. Within each subgroup, the processes are ranked in the 
        order defined by the value of the argument key, with ties broken according to their rank in the old group. 
        A new communicator is created for each subgroup and returned in newcomm. A process may supply the color value
        MPI_UNDEFINED, in which case newcomm returns MPI_COMM_NULL. This is a collective call, but each process is 
        permitted to provide different values for color and key.

        A call to MPI_COMM_CREATE(comm, group, newcomm) is equivalent to
        a call to MPI_COMM_SPLIT(comm, color, key, newcomm), where all members of group provide color~ =~0 and key~=~ 
        rank in group, and all processes that are not members of group provide color~ =~ MPI_UNDEFINED. The function 
        MPI_COMM_SPLIT allows more general partitioning of a group into one or more subgroups with optional reordering. 
       
        This call applies only intra-communicators.
        
        .. warning::
            This function is presently NOT IMPLEMENTED because it does not do anything that cannot otherwise be done with 
            groups (albeit this is simpler), and it requires special handling.
            Target implementation version: 1.1 
        """

        # one suggestion for implementation:
        # 1: collective exchange color/key info
        # 2: order into groups (each process will only be in one of N groups)
        # 2: order by respective key
        # 3: call comm_create lots of times
        

        raise NotImplementedException("comm_split targeted for version 1.1")
        if color is None:
            return None

    def comm_dup(self):
        """
        Duplicates the existing communicator comm with associated key values. For each key value,
        the respective copy callback function determines the attribute value associated with this 
        key in the new communicator; one particular action that a copy callback may take is to 
        delete the attribute from the new communicator. Returns in newcomm a new communicator with
        the same group, any copied cached information, but a new context (see http://www.mpi-forum.org/docs/mpi-11-html/node119.html#Node119).    
        
        .. note::Deviation: keys named MPI_* are considered internal and not copied. 
        
        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node102.html
        """
        new_comm = self.comm_create(self.group())
        for a in self.attr: # FIXME not tested
            if a.startswith("MPI_"):
                continue
            new_comm.attr[a] = copy.deepcopy(self.attr[a])
        
        new_comm._comm_call_attrs(type = self.comm_dup, calling_comm = new_comm, old_comm = self)
        return new_comm 

    def comm_compare(self, other_communicator):
        """
        MPI_IDENT results if and only if comm1 and comm2 is exactly the same object (identical groups and same contexts). 
        MPI_CONGRUENT results if the underlying groups are identical in constituents and rank order; these communicators differ only by context. 
        MPI_SIMILAR results if the group members of both communicators are the same but the rank order differs. 
        MPI_UNEQUAL results otherwise. 

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node101.html#Node101
        """
        
        if not isinstance(other_communicator, Communicator):
            return constants.MPI_UNEQUAL
        
        if self is other_communicator:
            return constants.MPI_IDENT
        
        ret = self.group().compare(other_communicator.group())
        if ret is constants.MPI_IDENT:
            return constants.MPI_CONGRUENT

        return ret

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
    # sendrecv_replace
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
    # MPI 2.0
    # mpi_start, mpi_start_all, mpi_xxx_init(...)
    # 
    # other stuff, related to requests that may get done:
    # MPI_TYPE_CREATE_DARRAY (Distributed Array Datatype Constructor)
    #
    def irecv(self, sender = constants.MPI_SOURCE_ANY, tag = constants.MPI_TAG_ANY):
        # Check that destination exists
        if not sender is constants.MPI_SOURCE_ANY and not self.have_rank(sender):
            raise MPINoSuchRankException("No process with rank %d in communicator %s. " % (sender, self.name))

        # Check that tag is valid
        if not isinstance(tag, int):
            raise MPIInvalidTagException("All tags should be integers")

        # Create a receive request object
        handle = Request("recv", self, sender, tag)

        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start. 
        with self.mpi.has_work_cond:
            with self.mpi.unstarted_requests_lock:
                self.mpi.unstarted_requests.append( handle )
                self.mpi.unstarted_requests_has_work.set()
            self.mpi.has_work_cond.notify()
        
        #Logger().debug("Irecv about to return - all locks released and notifies sent")

        return handle

    def isend(self, destination_rank, content, tag = constants.MPI_TAG_ANY):
        logger = Logger()
        # Check that destination exists
        if not self.have_rank(destination_rank):
            raise MPINoSuchRankException("Not process with rank %d in communicator %s. " % (destination_rank, self.name))

        # Check that tag is valid
        if not isinstance(tag, int):
            raise MPIInvalidTagException("All tags should be integers")

        # Create a send request object
        handle = Request("send", self, destination_rank, tag, False, data=content)
        
        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start. 
        with self.mpi.has_work_cond:
            with self.mpi.unstarted_requests_lock:
                self.mpi.unstarted_requests.append( handle )
                self.mpi.unstarted_requests_has_work.set()
            self.mpi.has_work_cond.notify()

        return handle

    def issend(self, destination_rank, content, tag = constants.MPI_TAG_ANY):
        """Synchronous send"""
        logger = Logger()
        # Check that destination exists
        if not self.have_rank(destination_rank):
            raise MPINoSuchRankException("Not process with rank %d in communicator %s. " % (destination_rank, self.name))

        # Check that tag is valid
        if not isinstance(tag, int):
            raise MPIInvalidTagException("All tags should be integers")

        # Create a send request object
        dummyhandle = Request("send", self, destination_rank, tag, True, data=content)
        
        # Create a recv request object to catch the acknowledgement message coming in
        # when this request is matched it also triggers the unacked->ready transition on the request handle
        handle = Request("recv", self, destination_rank, constants.TAG_ACK)
        #self.irecv(destination_rank, constants.TAG_ACK)
        
        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start. 
        with self.mpi.has_work_cond:
            with self.mpi.unstarted_requests_lock:
                self.mpi.unstarted_requests.append( dummyhandle )
                self.mpi.unstarted_requests.append( handle )
                self.mpi.unstarted_requests_has_work.set()
            self.mpi.has_work_cond.notify()

        return handle
        

    def ssend(self, destination, content, tag = constants.MPI_TAG_ANY):
        """Synchronous send"""
        return self.issend(destination, content, tag).wait()
        
    def send(self, destination, content, tag = constants.MPI_TAG_ANY):
        """
        Basic send function. Send to the destination rank a message
        with the specified tag. 

        This is a blocking operation. Look into isend if you can start your
        send early and do some computing while you wait for the send to 
        finish.

        **Example**
        Rank 0 sends "Hello world!" to rank 1. Rank 1 receives the message
        and prints it::
            
            from mpi import MPI
            mpi = MPI()
            TAG = 1 # optional. If omitted, MPI_TAG_ANY is assumed.

            if mpi.MPI_COMM_WORLD.rank() == 0:
                mpi.MPI_COMM_WORLD.send(1, "Hello World!", TAG)
            else:
                message = mpi.MPI_COMM_WORLD.recv(0, TAG)
                print message

        .. note::
            The above program will only work if run with -c 2 parameter (see
            :doc:`mpirun`). If invoked with more processes there will be size-2 
            processes waiting for a message that will never come. 

        POSSIBLE ERRORS: If you specify a destination rank out of scope for
        this communicator. 

        **See also**: :func:`recv` and :func:`isend`

        .. note::
            See the :ref:`TagRules` page for rules about your custom tags
        """
        return self.isend(destination, content, tag).wait()

    def recv(self, source, tag = constants.MPI_TAG_ANY):
        """
        Basic receive function. Receives from the destination rank a message
        with the specified tag. 

        This is a blocking operation. Look into irecv if you can start your
        receive early and do some computing while you wait for the receive
        result. 

        This method will not return if the destination process never sends data
        to this with the specified tag. See :func:`send` documentation for full
        working example. 

        POSSIBLE ERRORS: If you specify a destination rank out of scope for
        this communicator. 

        **See also**: :func:`irecv` and :func:`send`

        .. note::
            See the :ref:`TagRules` page for rules about your custom tags
        """
        return self.irecv(source, tag).wait()

    def sendrecv(self, senddata, dest, sendtag, source, recvtag):
        """
        The send-receive operations combine in one call the sending of a message to one destination and the receiving of another message, from another process.
        The two (source and destination) are possibly the same. 
        
        A send-receive operation is very useful for executing a shift operation across a chain of processes.
        A message sent by a send-receive operation can be received by a regular receive operation or probed by a probe operation; a send-receive operation can receive a message sent by a regular send operation. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node52.html
        """
        if dest == source:
            return senddata
            
        if source is not None:
            recvhandle = self.irecv(source, recvtag)
        
        if dest is not None:
            self.send(dest, senddata, sendtag)
            
        if source is not None:
            return recvhandle.wait()
            
        return None           
                

    def probe(self):
        Logger().warn("Non-Implemented method 'probe' called.")
        
    def barrier(self):
        """
        Blocks all the processes in the communicator until all have
        reached this call. 

        **Example usage**:
        The following code will iterate 10 loops in sync by calling 
        the barrier at the end of each loop::

            from mpi import MPI

            mpi = MPI()
            for i in range(10):
                # Do some tedious calculation here

                mpi.MPI_COMM_WORLD.barrier()
            mpi.finalize()

        """
        cr = CollectiveRequest(constants.TAG_BARRIER, self)
        return cr.wait()
        
    def bcast(self, root, data=None):
        """
        Broadcast a message (data) from the process with rank <root>
        to all other participants in the communicator. 

        This examples shows howto broadcast from rank 3 to all other
        processes who will print the message::

            from mpi import MPI

            mpi = MPI()
            if mpi.MPI_COMM_WORLD.rank() == 3:
                mpi.MPI_COMM_WORLD.bcast(3, "Test message")
            else:
                message = mpi.MPI_COMM_WORLD.bcast(3)
                print message

            mpi.finalize()

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node67.html
        """
        if self.rank() == root:
            # Start collective request
            if not data:
                raise MPIException("You need to specify data when you're the root of a broadcast")

        cr = CollectiveRequest(constants.TAG_BCAST, self, data, root=root)
        cr.complete_bcast()
        return cr.wait()

    def allgather(self, data):
        """
        The allgather function will gather all the data variables from the
        participants and return it in a rank-order. All the involced processes
        will receive the result.
        
        As an example each process can send it's rank::
        
            from mpi import MPI
            mpi = MPI()
            
            world = mpi.MPI_COMM_WORLD
            
            rank = world.rank()
            size = world.size()
            
            received = world.allgather(rank+1)
            
            assert received == range(1,size+1)
                
            mpi.finalize()
            
        """
        cr = CollectiveRequest(constants.TAG_ALLGATHER, self, data=data, start=False)
        cr.start_allgather()
        return cr.wait()

    def allreduce(self, data, op):
        """
        Combines values from all the processes with the op-function. You can write
        your own operations, see :ref:`the operations module <operations-api-label>`. There is also a number
        of predefined operations, like sum, average, min, max and prod. An example for
        writing a really bad factorial function would be::

            from mpi import MPI
            from mpi.operations import prod

            mpi = MPI()

            # We start n processes, and try to calculate n!
            rank = mpi.MPI_COMM_WORLD.rank()
            fact = mpi.MPI_COMM_WORLD.allreduce(rank, prod)

            print "I'm rank %d and I also got the result %d. So cool" % (rank, fact)

            mpi.finalize()

        Se also the :func:`reduce` function
        
        Original MPI 1.1 specification at FIXME

        .. note::
            The allreduce function will raise an exception if you pass anything
            else than a function as an operation. 
        """
        if not getattr(op, "__call__", False):
            raise MPIException("Operation should be a callable")

        cr = CollectiveRequest(constants.TAG_ALLREDUCE, self, data=data, start=False)
        cr.start_allreduce(op)
        return cr.wait()
        
    def alltoall(self, data):
        """
        This meethod extends the allgather in the situation where you need
        to send distinct data to each process. 
        
        The input data should be list with the same number of elements as
        the size of the communicator. If you supply something else an 
        Exception is raised. 
        
        If for example a process wants to send a string prefixed by the
        sending AND the recipient rank we could use the following code::
        
            from mpi import MPI
            
            mpi = MPI()
            
            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.rank()
            
            send_data = ["%d --> %d" % (rank, x) for x in range(size)]
            # For size of 4 and rank 2 this looks like
            # ['2 --> 0', '2 --> 1', '2 --> 2', '2 --> 3']
            
            recv_data = mpi.alltoall(send_data)
            
            # This will then look like the following (maybe not 
            # in this order). We're still rank 2
            # ['0 --> 2', '1 --> 2', '2 --> 2', '3 --> 2']
        """
        cr = CollectiveRequest(constants.TAG_ALLTOALL, self, data=data, start=False)
        cr.start_alltoall()
        return cr.wait()

    def gather(self, data, root=0):
        """
        Each process (root process included) sends the contents of its send buffer to the root 
        process. The root process receives the messages and stores them in rank order.
        
        As an example each of the processes could send their rank to the root::
        
            from mpi import MPI
            mpi = MPI()
            
            world = mpi.MPI_COMM_WORLD
            
            rank = world.rank()
            size = world.size()
            
            # Make every processes send their rank to the root. 
            
            ROOT = 3
            
            received = world.gather(rank+1, root=ROOT)
            
            if ROOT == rank:
                assert received == range(1, size+1)
            else:
                assert received == None
                
            mpi.finalize()
            
        ..note:: 
            If you need all the processes to receive the result you should look at allgather.  
        """
        cr = CollectiveRequest(constants.TAG_GATHER, self, data=data, start=False, root=root)
        cr.start_allgather()
        data = cr.wait()
        if self.rank() == root:
            return data
         
    def reduce(self, data, op, root=0):
        """
        Reduces the data given by each process by the "op" operator. As with
        the allreduce method you can "for example" use this to calculate the
        factorial number of size::
        
            from mpi import MPI
            from mpi.operations import prod
            
            mpi = MPI()
            
            root = 4
            
            # We start n processes, and try to calculate n!
            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()
            
            dist_fact = mpi.MPI_COMM_WORLD.reduce(rank+1, prod, root=root)
                
            mpi.finalize()
        """
        cr = CollectiveRequest(constants.TAG_REDUCE, self, data=data)
        cr.start_allreduce(op)
        data = cr.wait()

        if self.rank() == root:
            return data
    
    def reduce_scatter(self, arg):
        """
        MPI_REDUCE_SCATTER is functionally equivalent to MPI_REDUCE with count
        equal to the sum of recvcounts[i] followed by MPI_SCATTERV with sendcounts
        equal to recvcounts.
        """
        pass
        
    def scan(self, arg):
        """
        The scan function can be through of a partial reducing involving
        process 0 to i, where i is the rank of any given process in this
        communicator. 
        """
        pass
        
    def scatter(self, data=None, root=0):
        """
        Takes a SIZE list at the root and distibutes
        this to all the other processes in this communicator. The j'th
        element in the list will go to the process with rank j. 
        """
        if self.rank() == root and (data is None or not isinstance(data, list) or len(data) != self.size()):
            raise MPIException("Scatter used with invalid arguments.")
        
        identity = lambda x : x
        cr = CollectiveRequest(constants.TAG_SCATTER, self, data=data, root=root)
        cr.complete_bcast()
        data = cr.wait()

        return data[self.rank()]
        
    def test_cancelled(self):
        pass
    
    def testall(self, request_list):
        """
        Test if all the requests in the request list are finished. 
        """
        # We short circuit this so make it faster
        for request in request_list:
            if not request.test():
                return False
        return True
        
    def testany(self, request_list):
        """
        Test if any of the requests in the request list has completed and 
        return the first one it encounters. If none of the processes has
        completed the returned request will be None. 

        This function returns a tuple with a boolean flag to indicate if
        any of the requests is completed and the request object::

            from mpi import MPI
            mpi = MPI()

            ...

            (completed, request) = mpi.MPI_COMM_WORLD.testany(request_list)

            if completed:
                data = request.wait() # will return right away.. 
            else:
                pass # the request will be None
        """
        for request in request_list:
            if request.test():
                return (True, request)
        return (False, None)
    
    def testsome(self, request_list):
        """
        Tests that some of the operations has completed. Return a list
        of requst objects from that list that's completed. If none of
        the operations has completed the empty list is returned. 

        To receive a number of messages and print them you would do
        something like this::

            from mpi import MPI
            mpi = MPI()

            ...
            request_list = ...
            finished_requests = mpi.MPI_COMM_WORLD.testsome(request_list)
            data_list = mpi_MPI_COMM_WORLD.waitall(finished_requests)
            print "\\n".join(data_list)
        """
        return_list = []
        for request in request_list:
            if request.test():
                return_list.append( request )
        return return_list
        
    def topo_test(self):
        """docstring for topo_test"""
        pass
        
    def waitall(self, request_list):
        """
        Waits for all the requets in the given list and returns a list
        with the returned data. 

        **Example**
        Rank 0 sends 10 messages to and 1 and then receives 10. We're
        waiting for the receive completions with a waitall call::
            
            from mpi import MPI
            mpi = MPI()
            TAG = 1 # optional. If omitted, MPI_TAG_ANY is assumed.
            request_list = []

            if mpi.MPI_COMM_WORLD.rank() == 0:
                for i in range(10):
                    mpi.MPI_COMM_WORLD.send(1, "Hello World!", TAG)

                for i in range(10):
                    handle = mpi.MPI_COMM_WORLD.irecv(1, TAG)
                    request_list.append(handle)

                messages = mpi.MPI_COMM_WORLD.waitall(request_list)
            elif mpi.MPI_COMM_WORLD.rank() == 1:
                for i in range(10):
                    handle = mpi.MPI_COMM_WORLD.irecv(1, TAG)
                    request_list.append(handle)

                for i in range(10):
                    mpi.MPI_COMM_WORLD.send(1, "Hello World!", TAG)

                messages = mpi.MPI_COMM_WORLD.waitall(request_list)
            else:
                pass
        """
        return_list = []

        for request in request_list:
            data = request.wait()
            return_list.append(data)
        return return_list
        
    def waitany(self, request_list):
        """
        Wait for one request in the request list and return a tuple
        with the request and the data from the wait(). 

        This method will raise an MPIException if the supplied return_list
        is empty. 
        """
        if len(request_list) == 0:
            raise MPIException("The request_list argument to waitany can't be empty.. ")

        sleep_time = 0.1
        while True:
            for request in request_list:
                if request.test():
                    data = request.wait()
                    return (request, data)
            time.sleep(sleep_time)
            sleep_time *= 2

    def waitsome(self, request_list):
        """
        Waits for some requests in the given request list to 
        complete. Returns a list with (request, data) pairs
        for the completed requests. 

        If you want to receive a message from all the even
        ranks you could do it like this::

            from mpi import MPI
            mpi = MPI()
            world = mpi.MPI_COMM_WORLD
            request_list = []

            for rank in range(0, world.size(), 2):
                request = world.irecv(rank)
                request_list.append(request)

            while request_list:
                for item in world.waitsome(request_list):
                    (request, data) = item
                    print "Got message", data
                    request_list.remove(request)

        .. note::
            This function works in many aspects as the unix
            select functionality. You can use it as a simple
            way to just work on the messages that are actually
            ready without coding all the boilor plate yourself.

            Note however that it's not given that this function
            will include **all** the requests that are ready. It
            will however include **some**. 
        
        """
        return_list = []

        for request in request_list:
            if request.test():
                data = request.wait()
                return_list.append( (request, data))

        if return_list:
            return return_list

        return [ self.waitany(request_list) ]
        
    def Wtime(self):
        """
        returns a floating-point number of seconds, representing elapsed wall-clock 
        time since some time in the past. 
        
        .. note::
            *Deviation* MPI 1.1 states that "The 'time in the past' is guaranteed not to change during the life of the process. ".
            pupyMPI makes no such guarantee, however, it can only happen if the system clock is changed during a run.
        """
        
        return time.time() # TODO Improve clock function
        
    def Wtick(self):

        """
        returns the resolution of wtime() in seconds. That is, it returns, 
        as a double precision value, the number of seconds between successive clock ticks. For
        example, if the clock is implemented by the hardware as a counter that is incremented
        every millisecond, the value returned by wtick() should be 10 to the power of -3.
        """
        return 1.0 # TODO improve resolution detection
        
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
