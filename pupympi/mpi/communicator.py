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

import sys, copy, time

from mpi import constants
from mpi.exceptions import MPINoSuchRankException, MPIInvalidTagException, MPICommunicatorGroupNotSubsetOf, MPICommunicatorNoNewIdAvailable, MPIException, NotImplementedException, MPIInvalidRankException
from mpi.logger import Logger
from mpi.request import Request
from mpi.bc_tree import BroadCastTree
from mpi.collectiverequest import CollectiveRequest
from mpi.syscommands import handle_system_commands

class Communicator:

    def __init__(self, mpi, rank, size, network, group, id=0, name="MPI_COMM_WORLD", comm_root = None):
        self.mpi = mpi
        self.name = name
        self.network = network
        self.comm_group = group
        self.id = id
        self.id_ceiling = sys.maxint # for local communicator creation, can be deleted otherwise.
        self.MPI_COMM_WORLD = comm_root or self
        self.cmd = constants.CMD_USER

        self.mpi.communicators[self.id] = self

        self.attr = {}
        if name == "MPI_COMM_WORLD":
            self.attr = {   "MPI_TAG_UB": 2**30, \
                            "MPI_HOST": "TODO", \
                            "MPI_IO": rank, \
                            "MPI_WTIME_IS_GLOBAL": False
                        }


    def get_broadcast_tree(self, root=0):
        # Ensure we have the tree structure
        if not getattr(self, "bc_trees", None):
            self.bc_trees = {}

        # See if the tree root is actually present in this commnicator
        if not self.have_rank(root):
            raise MPINoSuchRankException("Invalid root. Not present in this communicator.")

        # Look for the root as key in the structure. If so we use this
        # tree as it has been generated earlier. This makes the system
        # act like a caching system, so we don't end up generating trees
        # all the time.
        if root not in self.bc_trees:
            #Logger().debug("Creating a new tree with root %d" % root)
            self.bc_trees[root] = BroadCastTree(range(self.size()), self.rank(), root)

        return self.bc_trees[root]

    def __repr__(self):
        return "<Communicator %s, id %s with %d members>" % (self.name, self.id, self.comm_group.size())

    def have_rank(self, rank):
        return rank in self.comm_group.members

    def get_network_details(self, rank):
        if not self.have_rank(rank):
            raise MPINoSuchRankException()

        return self.comm_group.members[rank]

    @handle_system_commands
    def rank(self):
        return self.comm_group.rank()

    @handle_system_commands
    def size(self):
        return self.comm_group.size()

    @handle_system_commands
    def group(self):
        """
        returns the group associated with a communicator
        """
        return self.comm_group

    @handle_system_commands
    def get_name(self):
        return self.name

    @handle_system_commands
    def set_name(self, name):
        self.name = name

    ################################################################################################################
    #### Communicator creation, deletion
    ################################################################################################################
    def _comm_call_attrs(self, **kwargs):
        """Iterates through each value in the cached attribute collection and calls the value if its callable"""
        for a in self.attr:
            if hasattr(self.attr[a], '__call__'):
                Logger().debug("Calling callback function on '%s'" % a)
                self.attr[a](self, **kwargs)
        # done

    @handle_system_commands
    def comm_create(self, group):
        """
        This function creates a new communicator with communication group
        defined by the group parameter and a new context. No cached information
        propagates from the existing communicator to the new. The function
        returns None to processes that are not in group.

        The call is erroneous if not all group arguments have the same value,
        or if group is not a subset of the group associated with comm.  Note
        that the call is to be executed by all processes in comm, even if they
        do not belong to the new group.

        .. note::
            This call is internally implemented either locally, in which case only 32 new communicators
            can be created across the lifespan of your MPI application, or collective with no (realistic) limit on
            the amount of created communicators but is significantly slower.

        """
        # check if group is a subset of this communicators' group
        for potential_new_member in group.members:
            if potential_new_member not in self.group().members:
                raise MPICommunicatorGroupNotSubsetOf(potential_new_member)

        if group.rank() == -1:
            return constants.MPI_COMM_NULL

        #return self._comm_create_coll(group)
        new_comm = self._comm_create_local(group)
        return new_comm

    ceiling = sys.maxint
    @handle_system_commands
    def _comm_create_local(self, group):
        """
        local only implementation. Can only handle log2(sys.maxint)-1 (ie 31 or 32) communicator creation depth/breadth.
        """
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

    @handle_system_commands
    def comm_free(self):
        """
        This operation marks the communicator object as closed.

        .. note::
            *Deviation:* This method deviates from the MPI standard by not being collective, and by not actually deallocating the object itself.

        """
        self.mpi._check_messages() # See documentation

        self._comm_call_attrs(type = self.comm_free, calling_comm = self)

        # thats it....dont do anything more. This deviates from the MPI standard.

    @handle_system_commands
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
        self.mpi._check_messages() # See documentation
        # one suggestion for implementation:
        # 1: collective exchange color/key info
        # 2: order into groups (each process will only be in one of N groups)
        # 2: order by respective key
        # 3: call comm_create lots of times


        raise NotImplementedException("comm_split targeted for version 1.1")
        if color is None:
            return None

    @handle_system_commands
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
        for a in self.attr:
            if a.startswith("MPI_"):
                continue
            new_comm.attr[a] = copy.deepcopy(self.attr[a])

        new_comm._comm_call_attrs(type = self.comm_dup, calling_comm = new_comm, old_comm = self)
        return new_comm

    @handle_system_commands
    def comm_compare(self, other_communicator):
        """
        MPI_IDENT results if and only if comm1 and comm2 is exactly the same object (identical groups and same contexts).
        MPI_CONGRUENT results if the underlying groups are identical in constituents and rank order; these communicators differ only by context.
        MPI_SIMILAR results if the group members of both communicators are the same but the rank order differs.
        MPI_UNEQUAL results otherwise.

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node101.html#Node101
        """
        self.mpi._check_messages() # See documentation
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

    def _direct_send(self, message, receivers=[], tag=constants.MPI_TAG_ANY):
        """
        A helper function for sending a message without passing the
        message through the queues. It's possible to send the same
        message to several recipients without having the data pickled
        multiple times.

        FIXME: The multiple-recipients way without picklign a lot of
               data could maybe be done with the regular send as well?
        """
        if not getattr(receivers, "__iter__", False):
            receivers = [receivers]

        return self.mpi.network._direct_send(self, message=message, receivers=receivers, tag=tag)

    @handle_system_commands
    def irecv(self, sender=constants.MPI_SOURCE_ANY, tag=constants.MPI_TAG_ANY):
        #Logger().debug(" -- irecv called -- sender:%s" % (sender) )
        """
        Starts a non-blocking receive, returning a handle like :func:`isend`. The
        following example shows how to prepare a receive request but perform some
        larger calculation while the MPI environment completes the receive::

            from mpi import MPI
            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            if world.rank() == 0:
                world.send( "My message", 1)
            else:
                handle = world.irecv(0)

                # Do some large calculation here
                pass

                # Receive the data from process 0
                data = handle.wait()

            mpi.finalize()

        .. note::
            It's possible for rank N to receive data from N.
        """
        return self._irecv(sender, tag)

    def _irecv(self, sender=constants.MPI_SOURCE_ANY, tag=constants.MPI_TAG_ANY):

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
        with self.mpi.pending_requests_lock:
            self.mpi.pending_requests.append(handle)
            self.mpi.pending_requests_has_work.set()
            self.mpi.has_work_event.set()

        return handle

    # Add an outbound request to the queue
    def _add_unstarted_request(self, requests):
        with self.mpi.unstarted_requests_lock:
            self.mpi.unstarted_requests.append( requests )
            self.mpi.unstarted_requests_has_work.set()
            self.mpi.has_work_event.set()

    # Add a request for communication with self
    def _send_to_self(self, request):
        # The sending request is complete, so we update it right away
        # so the user will be able to wait() for it.
        request.update("ready")

        queue_item = (self.rank(), request.tag, False, self.id, request.data)
        with self.mpi.received_data_lock:
            self.mpi.received_data.append(queue_item)
            self.mpi.pending_requests_has_work.set()
            self.mpi.has_work_event.set()


    @handle_system_commands
    def isend(self, content, destination, tag = constants.MPI_TAG_ANY):
        #Logger().debug(" -- isend called -- content:%s, destination:%s, tag:%s" % (content, destination, tag) )
        """
        Starts a non-blocking send. The function will return as soon as the
        data has been copied into a internal buffer making it safe for the
        user to alter the data.

        The function will return a handle making it possible :func:`cancel <mpi.request.Request.cancel>` the request,
        wait until the sending has completed or simply test if the request is
        complete like the following example shows::

            from mpi import MPI
            world = mpi.MPI_COMM_WORLD

            if world.rank() == 0:
                handle1 = world.isend("My message to 1", 1)
                handle2 = world.isend("My message to 2", 2)

                # Wait until the message to 1 is sent
                handle1.wait()

                # Check if the second message has completed. Cancel the
                # request otherwise
                if handle2.test():
                    handle2.wait() # This will complete right away
                                   # due to the test.
                else:
                    handle2.cancel()
            else:
                # This might not complete if the request gets
                # cancelled on the other end
                message = world.recv(0)

            mpi.finalize()

        .. note::
            It's possible for rank N to send data to N (itself). The data will **not**
            be transferred on the network but take a faster path.

        .. note::
            See also the :func:`send` and :func:`irecv` functions.
        """
        return self._isend(content, destination, tag)

    def _isend(self, content, destination, tag=constants.MPI_TAG_ANY, cmd=constants.CMD_USER):
        """
        An internal send function. It should only be used by the internal
        MPI environment. It gives some possibilities as it opens for other
        commands than CMD_USER.
        """
        # Check that destination exists
        if not self.have_rank(destination):
            if isinstance(destination, int):
                raise MPINoSuchRankException("No process with rank %d in communicator %s." % (destination, self.name))
            else:
                raise MPIInvalidRankException("Rank %s is not a valid rank (a rank should be an integer)." % (destination))

        # Check that tag is valid
        if not isinstance(tag, int):
            raise MPIInvalidTagException("All tags should be integers")
        # Create a send request object
        handle = Request("send", self, destination, tag, False, data=content, cmd=cmd)
        # If sending to self, take a short-cut
        if destination == self.rank():
            self._send_to_self(handle)
            return handle

        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start.
        self._add_unstarted_request(handle)
        return handle

    @handle_system_commands
    def issend(self, content, destination, tag = constants.MPI_TAG_ANY):
        """
        Synchronized non-blocking send function. The function will return as soon as the
        data has been copied into a internal buffer for subsequent sending.

        The function will return a handle to the request on which is is possible to
        :func:`cancel <mpi.request.Request.cancel>`, wait until the sending has
        completed or simply test if the request is complete.

        Until the receiving party in the communication has posted a receive of some
        kind matching the issend the request is not complete. Meaning that when
        a wait or a test on the request handle is succesful it is guaranteed that
        a matching receive is posted on the other side.

        **Example**
        Rank 0 posts an isend but rank 1 delays before posting a recieve that matches.
        Meanwhile rank 0 can test to see if the message got through::

            import time
            from mpi import MPI

            mpi = MPI()

            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()

            message = "Just a basic message from %d" % (rank)
            DUMMY_TAG = 1

            if rank == 0: # Send
                neighbour = 1
                handle = mpi.MPI_COMM_WORLD.issend(message, neighbour, DUMMY_TAG)

                # Since reciever waits 4 seconds before posting matching recieve
                # the first test should fail
                if not handle.test():
                    print "Yawn, still not getting through..."

                # By the time we wake up the receiver should have posted a
                # matching receive
                time.sleep(5)

                if handle.test():
                    print "Finally got through."

                handle.wait() # This is not strictly needed but good form

            elif rank == 1: # Recieve
                neighbour = 0
                time.sleep(4) # Wait a while to build tension

                recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)

            mpi.finalize()

        **See also**: :func:`ssend` and :func:`test`
        """
        # Check that destination exists
        if not self.have_rank(destination):
            if isinstance(destination, int):
                raise MPINoSuchRankException("No process with rank %d in communicator %s." % (destination, self.name))
            else:
                raise MPIInvalidRankException("Rank %s is not a valid rank (a rank should be an integer)." % (destination))

        # Check that tag is valid
        if not isinstance(tag, int):
            raise MPIInvalidTagException("All tags should be integers")

        # Create a send request object
        dummyhandle = Request("send", self, destination, tag, True, data=content)

        # Create a recv request object to catch the acknowledgement message coming in
        # when this request is matched it also triggers the unacked->ready transition on the request handle
        handle = Request("recv", self, destination, constants.TAG_ACK)
        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start.
        with self.mpi.pending_requests_lock:
            self.mpi.pending_requests.append(handle)
            self.mpi.pending_requests_has_work.set()
            self.mpi.has_work_event.set()

        # Add the request to the MPI layer unstarted requests queue. We
        # signal the condition variable to wake the MPI thread and have
        # it handle the request start.
        self._add_unstarted_request(dummyhandle)

        return handle

    @handle_system_commands
    def ssend(self, content, destination, tag = constants.MPI_TAG_ANY):
        """
        Synchronized send function. Send to the destination rank a message
        with the specified tag.

        Ssend blocks until a matching receieve is posted. That is when ssend
        returns you know the receiver has asked for something matching your
        message and most likely has also gotten the message.

        **Example**
        Rank 0 sends "Hello world!" to rank 1. Rank 1 posts a matching receive
        and rank 0 can be sure the message has gotten through.::

            from mpi import MPI
            mpi = MPI()
            TAG = 1 # optional. If omitted, MPI_TAG_ANY is assumed.

            if mpi.MPI_COMM_WORLD.rank() == 0:
                mpi.MPI_COMM_WORLD.ssend("Hello World!", 1, TAG)
                print "Now rank 1 must have asked for the message"
            elif mpi.MPI_COMM_WORLD.rank() == 1:
                message = mpi.MPI_COMM_WORLD.recv(0, TAG)
            else:
                pass

            mpi.finalize()

        POSSIBLE ERRORS: If you specify a destination rank out of scope for
        this communicator.

        **See also**: :func:`issend`

        .. note::
            See the :ref:`TagRules` page for rules about your custom tags
        """
        return self._ssend(content, destination, tag)

    def _ssend(self, content, destination, tag = constants.MPI_TAG_ANY):
        return _self.issend(content, destination, tag).wait()

    @handle_system_commands
    def send(self, content, destination, tag = constants.MPI_TAG_ANY):
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
                mpi.MPI_COMM_WORLD.send("Hello World!", 1, TAG)
            else:
                message = mpi.MPI_COMM_WORLD.recv(0, TAG)
                print message

            mpi.finalize()

        .. note::
            The above program will only work if run with -c 2 parameter (see
            :doc:`mpirun`). If invoked with more processes there will be size-2
            processes waiting for a message that will never come.

        .. note::
            It's possible for rank N to send data to N. The data will **not**
            be transferred on the network but take a faster path.

        POSSIBLE ERRORS: If you specify a destination rank out of scope for
        this communicator.

        **See also**: :func:`recv` and :func:`isend`

        .. note::
            See the :ref:`TagRules` page for rules about your custom tags
        """
        return self._send(content, destination, tag)

    def _send(self, content, destination, tag = constants.MPI_TAG_ANY):
        return self._isend(content, destination, tag).wait()

    @handle_system_commands
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

        .. note:: See also the :func:`irecv` and :func:`send` functions

        .. note::
            It's possible for rank N to receive data from N.

        .. note::
            See the :ref:`TagRules` page for rules about your custom tags
        """
        return self._recv(source, tag)

    def _recv(self, source, tag = constants.MPI_TAG_ANY):
        return self._irecv(source, tag).wait()

    @handle_system_commands
    def sendrecv(self, senddata, dest, sendtag, source, recvtag):
        """

        The send-receive operation combine in one call the sending of a message
        to one destination and the receiving of another message, from another destination.
        The two destinations can be the same.

        A send-receive operation is very useful for executing a shift operation
        across a chain of processes.
        A message sent by a send-receive operation can be received by a regular
        receive operation or probed by a probe operation; a send-receive operation
        can receive a message sent by a regular send operation.

        **Example usage**:
        The following code will send a token string between all messages. All
        ranks receive the token from their lower neighbour and pass it to the
        upper neighbour::

            from mpi import MPI

            mpi = MPI()

            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()

            content = "conch"
            DUMMY_TAG = 1

            # Send up in chain, recv from lower
            # modulo with size is to wrap around for lowest and highest rank
            dest   = (rank + 1) % size
            source = (rank - 1) % size

            recvdata = mpi.MPI_COMM_WORLD.sendrecv(content+" from "+str(rank),
                                                   dest,
                                                   DUMMY_TAG,
                                                   source,
                                                   DUMMY_TAG)
            print "Rank %i got %s" % (rank,recvdata)

            mpi.finalize()

        .. note::
            There is no sequential ordering here, as the print output will show. All
            that is guaranteed is that every process has sent and received, not in any
            particular order.

        """
        if dest == source:
            return senddata

        if source is not None:
            recvhandle = self._irecv(source, recvtag)

        if dest is not None:
            self._send(senddata, dest, sendtag)

        if source is not None:
            return recvhandle.wait()

        return None

    @handle_system_commands
    def probe(self):
        Logger().warn("Non-Implemented method 'probe' called.")

    @handle_system_commands
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

        The performance of the barrier function is the same as an :func:`bcast`
        call if the data in the call is small. Use this fact to piggybag data
        to other processes about status or whatever you need.

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.
        """
        cr = CollectiveRequest(constants.TAG_BARRIER, self)
        return cr.wait()

    @handle_system_commands
    def bcast(self, data=None, root=0):
        """
        Broadcast a message (data) from the process with rank <root>
        to all other participants in the communicator.

        This examples shows howto broadcast from rank 3 to all other
        processes who will print the message::

            from mpi import MPI

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            if world.rank() == 3:
                world.bcast("Test message", 3)
            else:
                message = world.bcast(root=3)
                print message

            mpi.finalize()

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            An :func:`MPINoSuchRankException <mpi.exceptions.MPINoSuchRankException>`
            is raised if the provided root is not a member of this communicator.
        """
        # Start collective request
        cr = CollectiveRequest(constants.TAG_BCAST, self, data, root=root)
        return cr.wait()

    @handle_system_commands
    def allgather(self, data):
        """
        The allgather function will gather all the data variables from the
        participants and return it in a rank-order. All the involved processes
        will receive the result.

        As an example each process can send its rank::

            from mpi import MPI
            mpi = MPI()

            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            received = world.allgather(rank)

            assert received == range(size)

            mpi.finalize()

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            See also the :func:`alltoall` function where each process sends
            individual data to each other process.

        """
        cr = CollectiveRequest(constants.TAG_ALLGATHER, self, data=data)
        return cr.wait()

    @handle_system_commands
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

        .. note::
            The allreduce function will raise an exception if you pass anything
            else than a function as an operation.

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            See also the :func:`reduce` and :func:`scan` functions.
        """
        if not getattr(op, "__call__", False):
            raise MPIException("The reduce operation supplied should be a callable")

        cr = CollectiveRequest(constants.TAG_ALLREDUCE, self, data=data, mpi_op=op)
        return cr.wait()

    @handle_system_commands
    def alltoall(self, data):
        """
        This meethod extends the :func:`scatter` in the situation where you
        need all-to-all instead of one-to-all.

        The input data should be list with the same number of elements as the
        size of the communicator. If you supply something else an Exception is
        raised.

        If for example a process wants to send a string prefixed by the sending
        AND the recipient rank we could use the following code::

            from mpi import MPI

            mpi = MPI()

            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.rank()

            send_data = ["%d --> %d" % (rank, x) for x in range(size)]
            # For size of 4 and rank 2 this looks like
            # ['2 --> 0', '2 --> 1', '2 --> 2', '2 --> 3']

            recv_data = mpi.alltoall(send_data)

            # This will then look like the following. We're still rank 2
            # ['0 --> 2', '1 --> 2', '2 --> 2', '3 --> 2']

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.
        """
        cr = CollectiveRequest(constants.TAG_ALLTOALL, self, data=data)
        return cr.wait()

    @handle_system_commands
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

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            An :func:`MPINoSuchRankException <mpi.exceptions.MPINoSuchRankException>`
            is raised if the provided root is not a member of this communicator.

        .. note::
            See also the :func:`allgather` and :func:`alltoall` functions.
        """
        cr = CollectiveRequest(constants.TAG_GATHER, self, data=data, root=root)
        data = cr.wait()
        if self.rank() == root:
            return data

    @handle_system_commands
    def reduce(self, data, op, root=0):
        """
        Reduces the data given by each process by the "op" operator. As with
        the allreduce method you can "for example" use this to calculate the
        factorial number of size::

            from mpi import MPI
            from mpi.operations import MPI_prod

            mpi = MPI()

            root = 4

            # We start n processes, and try to calculate n!
            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()

            dist_fact = mpi.MPI_COMM_WORLD.reduce(rank+1, MPI_prod, root=root)

            mpi.finalize()

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            An :func:`MPINoSuchRankException <mpi.exceptions.MPINoSuchRankException>`
            is raised if the provided root is not a member of this communicator.
        """
        if not getattr(op, "__call__", False):
            raise MPIException("The reduce operation supplied should be a callable")

        cr = CollectiveRequest(constants.TAG_REDUCE, self, data=data,root=root, mpi_op=op)
        data = cr.wait()

        if self.rank() == root:
            return data

    @handle_system_commands
    def scan(self, data, operation):
        """
        The scan function can be through of a partial reducing involving
        process 0 to i, where i is the rank of any given process in this
        communicator.

        To calculate the partial sum of the ranks upto the process self
        the following code could be used::

            from mpi import MPI
            mpi = MPI()

            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            partial_sum = world.scan(rank, sum)

            print "%d: Got partial sum of %d" % (rank, partial_sum)

            assert partial_sum == sum(range(rank+1))

            mpi.finalize()

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.
        """
        cr = CollectiveRequest(constants.TAG_SCAN, self, data=data, mpi_op=operation)
        return cr.wait()

    @handle_system_commands
    def scatter(self, data=None, root=0):
        """
        Takes a list with the size M*N, where N is also the number of participants
        in this communicator. It distributes the elements so each participant gets
        M elements. Notice the difference in scattering where M is 1 or above in the
        following example::

            from mpi import MPI

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            # Scatter a list with the same number of elements in the
            # list as there are processes in th world communicator

            SCATTER_ROOT = 3
            if rank == SCATTER_ROOT:
                scatter_data = range(size)
            else:
                scatter_data = None

            my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
            print "Rank %d:" % rank,  my_data

            # Scatter a list with 10 times the number of elements
            # in the list as there are processes in the world
            # communicator. This will give each process a list
            # with 10 items in it.

            if rank == SCATTER_ROOT:
                scatter_data = range(size*10)
            else:
                scatter_data = None

            my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
            print "Rank %d:" % rank,  my_data

            mpi.finalize()

        Running the above example with 5 processes will yield something
        like::

            Rank 4: 4
            Rank 2: 2
            Rank 1: 1
            Rank 3: 3
            Rank 0: 0
            Rank 2: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
            Rank 0: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            Rank 1: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
            Rank 4: [40, 41, 42, 43, 44, 45, 46, 47, 48, 49]
            Rank 3: [30, 31, 32, 33, 34, 35, 36, 37, 38, 39]

        .. note::
            All processes in the communicator **must** participate in this operation.
            The operation will block until every process has entered the call.

        .. note::
            An :func:`MPINoSuchRankException <mpi.exceptions.MPINoSuchRankException>`
            is raised if the provided root is not a member of this communicator.
        """
        if self.rank() == root and (not data or not getattr(data,"__iter__",False) or (len(data) % self.size() != 0)):
            raise MPIException("Scatter used with invalid arguments.")

        if self.rank() != root:
            data = None

        cr = CollectiveRequest(constants.TAG_SCATTER, self, data=data, root=root)
        return cr.wait()

    @handle_system_commands
    def testall(self, request_list):
        """
        Test if all the requests in the request list are finished. Returns a boolean
        indicating this. The following test shows the expected behaviour::

            from mpi import MPI
            import time

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            handles = []

            if rank == 0:
                # Sleep so the sending will be delayed
                time.sleep(3)

            for i in range(10):
                if rank == 0:
                    world.send( i, 1)
                else:
                    handle = world.irecv(0)
                    handles.append(handle)

            if rank == 1:
                # It will probably not be ready the first time
                ready = world.testall(handles)
                assert not ready

                # Give time time for the sending to complete
                time.sleep(4)

                # It should be ready now
                ready = world.testall(handles)
                assert ready

            mpi.finalize()
        """
        # We short circuit this to make it faster
        for request in request_list:
            if not request.test():
                return False
        return True

    @handle_system_commands
    def testany(self, request_list):
        """
        Test if any of the requests in the request list has completed and
        return the first one it encounters. If none of the processes has
        completed the returned request will be None.

        This function returns a tuple with a boolean flag to indicate if
        any of the requests is completed and the request object::

            from mpi import MPI
            from mpi import constants

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            handles = []

            for i in range(100):
                if rank == 0:
                    # This rank receives every message received by the other
                    # processes.
                    for j in range(size-1):
                        handle = world.irecv(constants.MPI_SOURCE_ANY)
                        handles.append(handle)

                    while handles:
                        (found, request) = world.testany(handles)
                        if found:
                            # Finish the request
                            request.wait()
                            handles.remove(request)

                else:
                    world.send( "My data", 0, constants.MPI_TAG_ANY)

            mpi.finalize()
        """
        for request in request_list:
            if request.test():
                return (True, request)
        return (False, None)

    @handle_system_commands
    def testsome(self, request_list):
        """
        Tests if some of the operations has completed. Return a list
        of requst objects from that list that's completed. If none of
        the operations has completed the empty list is returned.

        To receive a number of messages and print them you would do
        something like this::

            from mpi import MPI
            from mpi import constants

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD

            rank = world.rank()
            size = world.size()

            handles = []

            for i in range(100):
                if rank == 0:
                    # This rank receives every message received by the other
                    # processes.
                    for j in range(size-1):
                        handle = world.irecv(constants.MPI_SOURCE_ANY)
                        handles.append(handle)

                    while handles:
                        request_list = world.testsome(handles)
                        if request_list:
                            # Finish the request
                            data_list = world.waitall(request_list)
                            print "\\n".join(data_list)
                            handles = [ r for r in handles if r not in request_list]

                else:
                    world.send("My data", 0, constants.MPI_TAG_ANY)

            mpi.finalize()
        """
        return_list = []
        for request in request_list:
            if request.test():
                return_list.append( request )
        return return_list

    @handle_system_commands
    def waitall(self, request_list):
        """
        Waits for all the requests in the given list and returns a list
        with the returned data.

        **Example**
        Rank 0 sends 10 messages to and 1 and then receives 10. We're
        waiting for the receive completions with a waitall call::

            from mpi import MPI

            mpi = MPI()
            rank = mpi.MPI_COMM_WORLD.rank()
            size = mpi.MPI_COMM_WORLD.size()

            request_list = []

            if mpi.MPI_COMM_WORLD.rank() == 0:
                for i in range(10):
                    mpi.MPI_COMM_WORLD.send(1, "Hello World!")

                for i in range(10):
                    handle = mpi.MPI_COMM_WORLD.irecv(1)
                    request_list.append(handle)

                messages = mpi.MPI_COMM_WORLD.waitall(request_list)
            elif mpi.MPI_COMM_WORLD.rank() == 1:
                for i in range(10):
                    handle = mpi.MPI_COMM_WORLD.irecv(0)
                    request_list.append(handle)

                for i in range(10):
                    mpi.MPI_COMM_WORLD.send( "Hello World!", 0)

                messages = mpi.MPI_COMM_WORLD.waitall(request_list)
            else:
                pass

            mpi.finalize()

        .. note::
            See also the :func:`waitany` and :func:`waitsome` functions.
        """
        return self._waitall(request_list)

    def _waitall(self, request_list):
        remaining = len(request_list)
        incomplete = [True for _ in range(remaining)]
        return_list = [None for _ in range(remaining)]

        while remaining > 0:
            for idx, request in enumerate(request_list):
                if incomplete[idx] and request.test():
                    return_list[idx] = request.wait()
                    incomplete[idx] = False
                    remaining -= 1

            time.sleep(0.00001)

        return return_list

    @handle_system_commands
    def waitany(self, request_list):
        """
        Wait for **one** request in the request list and return a tuple
        with the request and the data from the wait().

        This method will raise an MPIException if the supplied return_list
        is empty.

        The following example shows rank 0 receiving 10 messages
        from every other process. Rank 0 wait for one request at
        the time, but does not specify which one. This allows for
        smoother progres::

            from mpi import MPI

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD
            request_list = []

            if world.rank() == 0:
                for i in range(10):
                    for rank in range(0, world.size()):
                        if rank != 0:
                            request = world.irecv(rank)
                            request_list.append(request)

                while request_list:
                    (request, data) =  world.waitany(request_list)
                    request_list.remove(request)
            else:
                for i in range(10):
                    world.send( "Message", 0)

            mpi.finalize()

        .. note::
            See also the :func:`waitall` and :func:`waitsome` functions.
        """
        return self._waitany(request_list)

    def _waitany(self, request_list):
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

    @handle_system_commands
    def waitsome(self, request_list):
        """
        Waits for some requests in the given request list to
        complete. Returns a list with (request, data) pairs
        for the completed requests.

        The following example shows rank 0 receiving 10 messages
        from every other process. Instead of waiting for each
        one sequentially or waiting for them all at the same time
        it's possible to fetch the already completed handles::

            from mpi import MPI

            mpi = MPI()
            world = mpi.MPI_COMM_WORLD
            request_list = []

            if world.rank() == 0:
                for i in range(10):
                    for rank in range(0, world.size()):
                        if rank != 0:
                            request = world.irecv(rank)
                            request_list.append(request)

                while request_list:
                    items =  world.waitsome(request_list)
                    print "Waited for %d handles" % len(items)
                    for item in items:
                        (request, data) = item
                        request_list.remove(request)
            else:
                for i in range(10):
                    world.send( "Message", 0)

            mpi.finalize()

        One possible output from the above code (with 10 processes)
        is::

            Waited for 1 handles
            Waited for 45 handles
            Waited for 31 handles
            Waited for 1 handles
            Waited for 12 handles

        .. note::
            See also the :func:`waitany` and :func:`waitall` functions.

        .. note::
            This function works in many aspects as the unix
            select functionality. You can use it as a simple
            way to just work on the messages that are actually
            ready without coding all the boiler-plate yourself.

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

        return [ self._waitany(request_list) ]

    @handle_system_commands
    def Wtime(self):
        """
        returns a floating-point number of seconds, representing elapsed wall-clock
        time since some time in the past.

        .. note::
            *Deviation* MPI 1.1 states that "The 'time in the past' is guaranteed not to change during the life of the process. ".
            pupyMPI makes no such guarantee, however, it can only happen if the system clock is changed during a run.
        """

        return time.time()

    @handle_system_commands
    def Wtick(self):
        """
        returns the resolution of wtime() in seconds. That is, it returns,
        as a double precision value, the number of seconds between successive clock ticks. For
        example, if the clock is implemented by the hardware as a counter that is incremented
        every millisecond, the value returned by wtick() should be 10 to the power of -3.
        """
        return 1.0

    ################################################################################################################
    # LOCAL OPERATIONS
    ################################################################################################################

    #### Inter-communicator operations
    def test_inter(self):
        """
        This local routine allows the calling process to determine if a communicator is an inter-communicator or an intra-communicator. It returns true if it is an inter-communicator, otherwise false.

        http://www.mpi-forum.org/docs/mpi-11-html/node112.html
        """
        return False
