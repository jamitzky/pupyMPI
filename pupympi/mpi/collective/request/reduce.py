from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi.exceptions import MPIException

from mpi import constants
from mpi.logger import Logger

from mpi.topology import tree

import copy

try:
    import numpy
except ImportError:
    numpy = None


def reduce_elementwise(sequences, operation):
    """
    Perform a element-wise reduction on elements of equal length sequences
    
    Sequences can be everything iterable
    """
    """
    mapping and zipping like there's no tomorrow
    """
    first = sequences[0]
    
    print "-"*40
    for s in sequences:
        print "type: ", type(s)
        print "len: ", len(s)
    print "-"*40
    
    numpy_op = getattr(operation, "numpy_op", None)
    
    if numpy and numpy_op and isinstance(first, numpy.ndarray) and first.dtype.kind in ("i", "f"):
        m = numpy.matrix(sequences)
        reduced_results = getattr(m, numpy_op)(0)
    else:    
        reduced_results = map(operation,zip(*sequences))
    
    # Restore the type of the sequence
    if isinstance(sequences[0],str):    
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
    if isinstance(sequences[0],numpy.ndarray): # Get 1 dimensional numpy array from numpy matrix
        reduced_results = reduced_results.A[0]
        
    return reduced_results

class TreeAllReduce(BaseCollectiveRequest):
    
    SETTINGS_PREFIX = "ALLREDUCE"
    
    def __init__(self, communicator, data, operation, tag=constants.TAG_ALLREDUCE):
        super(TreeAllReduce, self).__init__()

        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.root = 0
        self.tag = tag

        self.operation = operation
        self.unpack = False # should we unpack a list to a simpler type (see next if)
        
        #if not getattr(data, "__iter__", False):
        if not (hasattr(data,"index") or isinstance(data, numpy.ndarray)):
            data = [data]
            self.unpack = True
            
        self.data = data
        self.partial = getattr(operation, "partial_data", False)

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        self.received_data = {}
        self.missing_children = copy.copy(self.children)
        self.phase = "up"

        # The all reduce operation is handled by receiving data from each
        # child, reduce the data, and send the result to the parent.
        if not self.children:
            # We dont wait for messages, we simply send our data to the parent.
            self.data = {self.rank : self.data}
            self.to_parent()

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if self.phase == "up":
            if rank not in self.missing_children:
                return False

            # Remove the rank from the missing children.
            self.missing_children.remove(rank)

            # Add the data to the list of received data
            self.received_data.update(data)

            # If the list of missing children i empty we have received from
            # every child and can reduce the data and send to the parent.
            if not self.missing_children:
                # Add our own data element
                self.received_data[self.rank] = self.data                
                
                # reduce the data
                if self.partial:
                    print "type", type(self.received_data.values()[0]), self.received_data.values()[0]
                    new_data = reduce_elementwise(self.received_data.values(), self.operation)
                        
                    self.data = {self.rank : new_data}
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
            val = self.data[self.root]
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
        self.communicator._direct_send(self.data, receivers=self.children, tag=self.tag)
        self._finished.set()

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            self.communicator._isend(self.data, self.parent, tag=self.tag)

        self.phase = "down"

        if self.parent is None:
            # Clean data if possible.
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

# ------------------------ reduce operation below ------------------------
class TreeReduce(BaseCollectiveRequest):
    
    SETTINGS_PREFIX = "REDUCE"
    
    def __init__(self, communicator, data, operation, root=0):
        super(TreeReduce, self).__init__()

        self.unpack = False
        #if not getattr(data, "__iter__", False):
        if not hasattr(data,"index"):
            data = [data]
            self.unpack = True

        self.data = data
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        self.root = root

        self.operation = operation
        if not getattr(self, "partial", None):
            self.partial = getattr(operation, "partial_data", False)

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant reduce without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        self.received_data = {}
        self.missing_children = copy.copy(self.children)

        # The all reduce operation is handled by receiving data from each
        # child, reduce the data, and send the result to the parent.
        if not self.children:
            # We dont wait for messages, we simply send our data to the parent.
            self.data = {self.rank : self.data}
            self.to_parent()

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.

        if self._finished.is_set():
            return False

        if rank not in self.missing_children:
            return False

        # Remove the rank from the missing children.
        self.missing_children.remove(rank)

        # Add the data to the list of received data
        self.received_data.update(data)

        # If the list of missing children i empty we have received from
        # every child and can reduce the data and send to the parent.
        if not self.missing_children:
            # Add our own data element
            self.received_data[self.rank] = self.data

            # reduce the data
            if self.partial:
                new_data = reduce_elementwise(self.received_data.values(), self.operation)
                self.data = {self.rank : new_data}
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
            val = self.data[self.root]
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
            self.communicator._isend(self.data, self.parent, tag=constants.TAG_REDUCE)

        self._finished.set()

class FlatTreeReduce(FlatTreeAccepter, TreeReduce):
    pass

class BinomialTreeReduce(BinomialTreeAccepter, TreeReduce):
    pass

class StaticTreeReduce(StaticFanoutTreeAccepter, TreeReduce):
    pass
# ------------------------ scan operation below ------------------------
class TreeScan(TreeAllReduce):
    
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
