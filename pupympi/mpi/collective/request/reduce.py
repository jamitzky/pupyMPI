from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi.exceptions import MPIException

from mpi import constants
from mpi.logger import Logger
from mpi import utils

from mpi.topology import tree
from mpi.commons import numpy

import copy

def reduce_elementwise(sequences, operation):
    """
    Perform a element-wise reduction on elements of equal length sequences

    Sequences can be everything iterable
    """
    # Check if a pupyMPI/numpy operation exists for this operation
    numpy_op = getattr(operation, "numpy_op", None)

    # If it is a numpy array and an optimized operation exists we use it
    if isinstance(sequences[0], numpy.ndarray) and numpy_op:
        reduced_results = numpy_op(sequences,dtype=sequences[0].dtype)
    else:
        reduced_results = map(operation,zip(*sequences))

        # Restore the type of the sequence
        if isinstance(sequences[0],numpy.ndarray):
            reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
        if isinstance(sequences[0],str):
            reduced_results = ''.join(reduced_results) # join char list into string
        if isinstance(sequences[0],bytearray):
            reduced_results = bytearray(reduced_results) # make byte list into bytearray
        if isinstance(sequences[0],tuple):
            reduced_results = tuple(reduced_results) # join

    return reduced_results

class TreeAllReduce(BaseCollectiveRequest):
    """
    The allreduce operation is handled by receiving data from each
    child, reducing the data at the root node, potentially with some partial
    reduction along the way at intermediate nodes.
    The reduced result is then broadcast back down the tree to all nodes.
    """

    SETTINGS_PREFIX = "ALLREDUCE"

    def __init__(self, communicator, data, operation, tag=constants.TAG_ALLREDUCE):
        super(TreeAllReduce, self).__init__(communicator, data, operation, tag=constants.TAG_ALLREDUCE)

        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.root = 0
        self.tag = tag

        self.operation = operation
        self.unpack = False # should we unpack a list to a simpler type (see next if)

        # If not sliceable we are dealing with a bool or integer and box it into a list for convenience
        if not (hasattr(data,"index") or isinstance(data, numpy.ndarray)):
            data = [data]
            self.unpack = True # Mark that data should be unboxed later

        self.data = data
        self.partial = getattr(operation, "partial_data", False) # Does the reduce operation allow partial reduction

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        self.received_data = {}
        self.missing_children = copy.copy(self.children)
        self.phase = "up"

        # Leaf nodes don't wait for children
        if not self.children:
            # We dont wait for messages, we simply send our data to the parent.
            if not self.partial:
                # On partial reduce we keep the data as is to ensure flexible serialization
                # but otherwise we transmit it in a nice dict to ensure rank order
                # FIXME: This is premature, put it in dict (if need be) at intermediate nodes only
                self.data = {self.rank : self.data}
            self.to_parent()

    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        # Deserialize data
        data = utils.deserialize_message(raw_data, msg_type)

        if self.phase == "up":
            if rank not in self.missing_children:
                return False

            # Remove the rank from the missing children.
            self.missing_children.remove(rank)

            # Add the data to the list of received data
            if self.partial:
                # If partial reduce we didn't get a dict but just the reduced data
                self.received_data[rank] = data
            else:
                self.received_data.update(data)

            # When the list of missing children is empty we have received from
            # every child and can reduce the data and send to the parent.
            if not self.missing_children:
                # Add our own data element
                self.received_data[self.rank] = self.data

                # reduce the data
                if self.partial:
                    self.data = reduce_elementwise(self.received_data.values(), self.operation)
                else:
                    self.data = self.received_data

                # forward to the parent.
                self.to_parent()
            return True
        elif self.phase == "down":
            if rank != self.parent:
                return False

            self.data = data
            self.to_children()
            return True
        else:
            Logger().warning("Accept_msg in unknown phase: %s" % self.phase)

        return False

    def _get_data(self):
        val = None
        if self.partial:
            val = self.data
        else:
            keys = self.data.keys()
            keys.sort()
            ready_data = []
            for k in keys:
                ready_data.append( self.data[k] )

            val = reduce_elementwise(ready_data, self.operation)

        if self.unpack:
            return val[0]
        else:
            return val

    def to_children(self):
        self.direct_send(self.data, receivers=self.children, tag=self.tag, serialized=False)
        self.done()

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            self.isend(self.data, self.parent, tag=self.tag)

        self.phase = "down" # Mark next phase as begun

        if self.parent is None:
            # Clean data if needed
            # (this is only the case if the allreduce is used for a scan operation)
            cleaner = getattr(self, "clean_data", None)
            if cleaner:
                cleaner()

            # We are the root, so we have the final data. Broadcast to the children
            self.to_children()


class FlatTreeAllReduce(FlatTreeAccepter, TreeAllReduce):
    pass

class BinomialTreeAllReduce(BinomialTreeAccepter, TreeAllReduce):
    pass

class StaticTreeAllReduce(StaticFanoutTreeAccepter, TreeAllReduce):
    pass


class TreeAllReducePickless(BaseCollectiveRequest):
    """
    """

    SETTINGS_PREFIX = "ALLREDUCEPL"

    def __init__(self, communicator, data, operation, tag=constants.TAG_ALLREDUCE):
        super(TreeAllReducePickless, self).__init__(communicator, data, operation, tag=constants.TAG_ALLREDUCE)

        self.communicator = communicator
        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.root = 0
        self.operation = operation

        self.data_list = [None] * self.size
        self.data_list[self.rank],self.msg_type,self.chunksize  = utils.serialize_message(data)        

        self.partial = False # No partial reduction for now

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        self.received_data = {}
        self.missing_children = copy.copy(self.children)
        self.phase = "up"

        # Leaf nodes don't wait for children
        if not self.children:
            self.to_parent()

    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if self.phase == "up":
            if rank not in self.missing_children:
                return False

            # Remove the rank from the missing children.
            self.missing_children.remove(rank)

            desc = self.topology.descendants(rank)
            all_ranks = [rank]+desc # All the ranks having a payload in this message
            all_ranks.sort() # keep it sorted

            # Store payloads in proper positions
            for i,r in enumerate(all_ranks):
                pos_r = i
                begin = pos_r * (self.chunksize)
                end = begin + (self.chunksize)
                # Add the data to the list of received data
                self.data_list[r] = [raw_data[begin:end]]

            # When the list of missing children is empty we have received from
            # every child and can reduce the data and send to the parent.
            if not self.missing_children:
                # forward to the parent.
                self.to_parent()
            return True

        elif self.phase == "down":
            if rank != self.parent:
                return False

            # FIXME: just fix!
            self.data_list = raw_data
            self.to_children()
            return True
        else:
            Logger().warning("Accept_msg in unknown phase: %s" % self.phase)

        return False

    def _get_data(self):
        return utils.deserialize_message(self.data_list, self.msg_type)

    def to_children(self):
        self.direct_send(self.data_list, receivers=self.children, tag=self.tag, serialized=True)
        self.done()

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            #payloads = [d for d in self.data_list if d is not None]
            payloads = [d for dl in self.data_list if dl is not None for d in dl] # flatten the lists that are not None
            Logger().warning("Sending to_parent payloads: %s combined-len:%i passed-len:%s" % (payloads, sum(map(len,payloads)), len(payloads)*self.chunksize) )
            self.multisend(payloads, self.parent, tag=constants.TAG_ALLREDUCE, cmd=self.msg_type, payload_length=len(payloads)*self.chunksize)

        self.phase = "down" # Mark next phase as begun

        if self.parent is None:
            # Clean data if needed
            # (this is only the case if the allreduce is used for a scan operation)
            cleaner = getattr(self, "clean_data", None)
            if cleaner:
                cleaner()

            # We are the root, so we have the final data.
            # Perform reduce and broadcast to the children
            # Deserialize all payloads before reduction
            for r in range(self.size):
                self.data_list[r] = utils.deserialize_message(self.data_list[r], self.msg_type)
            val = reduce_elementwise(self.data_list, self.operation)

            self.data_list,self.msg_type,_ = utils.serialize_message(val)
            self.to_children()

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        """
        Accept as long as it is numpy array or bytearray
        """
        if isinstance(kwargs['data'], numpy.ndarray) or isinstance(kwargs['data'],bytearray):
            obj = cls(communicator, *args, **kwargs)

            # Check if the topology is in the cache
            root = kwargs.get("root", 0)
            cache_idx = "tree_binomial_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.BinomialTree(size=communicator.size(), rank=communicator.rank(), root=root)
                cache.set(cache_idx, topology)

            obj.topology = topology
            return obj

class BinomialTreeAllReducePickless(TreeAllReducePickless):
    pass

# ------------------------ reduce operation below ------------------------
class TreeReduce(BaseCollectiveRequest):

    SETTINGS_PREFIX = "REDUCE"

    def __init__(self, communicator, data, operation, root=0):
        super(TreeReduce, self).__init__(communicator, data, operation, root=root)

        self.unpack = False
        #if not getattr(data, "__iter__", False):

        # the attribute index is found on strings (which __iter__ is not) but excludes numpy arrays
        if not (hasattr(data,"index") or isinstance(data, numpy.ndarray)):
            data = [data]
            self.unpack = True

        self.data = data
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        self.root = root

        self.operation = operation

        if not hasattr(self, "partial"):
            self.partial = getattr(operation, "partial_data", False)

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()
        self.received_data = {}

        self.missing_children = copy.copy(self.children)

        # Leaf nodes don't wait for children
        if not self.children:
            # We dont wait for messages, we simply send our data to the parent.
            if not self.partial:
                # On partial reduce we keep the data as is to ensure flexible serialization
                # but otherwise we transmit it in a nice dict to ensure rank order
                # FIXME: This is premature, put it in dict (if need be) at intermediate nodes only
                self.data = {self.rank : self.data}
            self.to_parent()

    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.

        if self._finished.is_set():
            return False

        if rank not in self.missing_children:
            return False

        # Remove the rank from the missing children.
        self.missing_children.remove(rank)

        data = utils.deserialize_message(raw_data, msg_type)
        # Add the data to the list of received data
        if self.partial:
            # If partial reduce we didn't get a dict but just the reduced data
            self.received_data[rank] = data
        else:
            self.received_data.update(data)

        # If the list of missing children is empty we have received from
        # every child and can reduce the data and send to the parent.
        if not self.missing_children:
            # Add our own data element
            self.received_data[self.rank] = self.data

            # reduce the data
            if self.partial:
                #new_data = reduce_elementwise(self.received_data.values(), self.operation)
                #self.data = {self.rank : new_data}
                self.data = reduce_elementwise(self.received_data.values(), self.operation)
            else:
                self.data = self.received_data

            # forward to the parent.
            self.to_parent()
        return True

    def _get_data(self):
        if self.rank != self.root:
            return None

        val = None

        if self.partial:
            #val = self.data[self.root]
            val = self.data
        else:
            keys = self.data.keys()
            keys.sort()
            ready_data = []
            for k in keys:
                ready_data.append( self.data[k] )

            val = reduce_elementwise(ready_data, self.operation)

        if self.unpack:
            return val[0]
        else:
            return val

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            self.isend(self.data, self.parent, tag=constants.TAG_REDUCE)

        self.done()

class FlatTreeReduce(FlatTreeAccepter, TreeReduce):
    pass

class BinomialTreeReduce(BinomialTreeAccepter, TreeReduce):
    pass

class StaticTreeReduce(StaticFanoutTreeAccepter, TreeReduce):
    pass

class TreeReducePickless(BaseCollectiveRequest):
    """
    Flexible serialization for the types that can handle it.
    Only serializing at source and deserializing at root.
    Since data remains serialized at intermediate nodes there is no partial
    reduction.

    ISSUES:
    - Using the rank indexed data list is kinda clumsy
    - bytearrays and numpy arrays with elements of 1 byte (eg. bool, 8 bit ints etc.)
      should in many cases be partially reducible even though serialized.
    """

    SETTINGS_PREFIX = "REDUCEPL"

    def __init__(self, communicator, data, operation, root=0):
        super(TreeReducePickless, self).__init__(communicator, data, operation, root=root)

        self.communicator = communicator
        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.root = root
        self.operation = operation

        self.data_list = [None] * self.size
        self.data_list[self.rank],self.msg_type,self.chunksize  = utils.serialize_message(data)

        self.partial = False # No partial reduction for now

        ## Partial reduction should be done if bytesize allows and operation is listed as allowing it
        #if not hasattr(self, "partial") and (len(data) == self.chunksize):
        #    self.partial = getattr(operation, "partial_data", False)
        #else:
        #    self.partial = False

        #Logger().debug("PICKLESS REDUCE partial:%s" % self.partial)

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()
        self.received_data = {}

        self.missing_children = copy.copy(self.children)

        # Leaf nodes don't wait for children
        if not self.children:
            self.to_parent()

    def accept_msg(self, child_rank, raw_data, msg_type):
        Logger().debug("PICKLESSREDUCE ACCEPT rank:%i" % self.rank)
        # Do not do anything if the request is completed.

        if self._finished.is_set():
            return False

        if child_rank not in self.missing_children:
            return False

        # Remove the rank from the missing children.
        self.missing_children.remove(child_rank)

        desc = self.topology.descendants(child_rank)
        all_ranks = [child_rank]+desc # All the ranks having a payload in this message
        all_ranks.sort() # keep it sorted

        # Store payloads in proper positions
        for i,r in enumerate(all_ranks):
            pos_r = i
            begin = pos_r * (self.chunksize)
            end = begin + (self.chunksize)
            # Add the data to the list of received data
            # NOTE: Boxing
            self.data_list[r] = [raw_data[begin:end]]

        # If the list of missing children is empty we have received from
        # every child and can reduce the data and send to the parent.
        if not self.missing_children:
            ## reduce the data before passing on
            #if self.partial:
            #    self.data_list[self.rank] = reduce_elementwise([d for d in self.data_list if d != None], self.operation)

            # forward to the parent.
            self.to_parent()
        return True

    def _get_data(self):
        if self.rank != self.root:
            return None

        val = None

        # Deserialize all payloads before reduction
        for r in range(self.size):
            self.data_list[r] = utils.deserialize_message(self.data_list[r], self.msg_type)
        val = reduce_elementwise(self.data_list, self.operation)

        return val

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            if self.partial:
                # With partial reduce we only send the reduced value up
                # NOTE: Avoid stupid list boxing
                payloads = [self.data_list[self.rank]]
            else:
                #payloads = [d for d in self.data_list if d is not None]
                payloads = [d for dl in self.data_list if dl is not None for d in dl] # flatten the lists that are not None                
            self.multisend(payloads, self.parent, tag=constants.TAG_REDUCE, cmd=self.msg_type, payload_length=len(payloads)*self.chunksize)

        self.done()


    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        """
        Accept as long as it is numpy array or bytearray
        """
        if isinstance(kwargs['data'], numpy.ndarray) or isinstance(kwargs['data'],bytearray):
            obj = cls(communicator, *args, **kwargs)

            # Check if the topology is in the cache
            root = kwargs.get("root", 0)
            cache_idx = "tree_binomial_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.BinomialTree(size=communicator.size(), rank=communicator.rank(), root=root)
                cache.set(cache_idx, topology)

            obj.topology = topology
            return obj

class BinomialTreeReducePickless(TreeReducePickless):
    pass


# ------------------------ scan operation below ------------------------
class TreeScan(TreeAllReduce):
    """
    TreeScan implements the scan operation as a TreeAllReduce with no partial
    reduction where input from ranks above self are not used in the reduction
    operation, as specified by MPI semantics.
    """

    SETTINGS_PREFIX = "SCAN"

    def __init__(self, communicator, data, operation):
        self.partial = False
        super(TreeScan, self).__init__(communicator, data, operation, tag=constants.TAG_SCAN)

    def clean_data(self):
        keys = self.data.keys()
        keys.sort()

        final_data = {}
        so_far = []

        for rank in keys:
            data = self.data[rank]
            so_far.append(data)

            # Element wise operation
            new_data = []
            for i in range(len(so_far[0])):
                vals = []
                for alist in so_far:
                    vals.append(alist[i])
                new_data.append(self.operation(vals))
            reduced = new_data

            if self.unpack:
                reduced = reduced[0]

            final_data[rank] = reduced

        self.data = final_data

    def _get_data(self):
        return self.data[self.rank]

class FlatTreeScan(FlatTreeAccepter, TreeScan):
    pass

class BinomialTreeScan(BinomialTreeAccepter, TreeScan):
    pass

class StaticFanoutTreeScan(StaticFanoutTreeAccepter, TreeScan):
    pass
