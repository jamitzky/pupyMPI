from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger
from mpi.topology import tree

from math import log
import copy

class DisseminationAllGather(BaseCollectiveRequest):
    def __init__(self, communicator, data):
        super(DisseminationAllGather, self).__init__()

        self.data = data
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

    def start(self):
        # Do some initial calculation.
        self.data_list = [None] * self.size
        self.data_list[self.rank] = self.data

        self.iterations = int(log(self.size, 2))
        self.gap_size = self.size - 2**self.iterations
        self.i = 0

        self.phase = "normal"

        self.iterate()

    @classmethod
    def accept(cls, *args, **kwargs):
        """
        This implementation is so supreme that we accept problems of any sizes
        and layout. GO TEAM DISSEMINATION.
        """
        return cls(*args, **kwargs)

    def iterate(self):
        send_to = (2**self.i+self.rank) % self.size
        self.recv_from = (self.rank - (2**self.i)) % self.size

        self.communicator._isend(self.data_list, send_to, constants.TAG_ALLGATHER)

    def accept_msg(self, rank, data):
        if self._finished.is_set() or rank != self.recv_from:
            return False

        if self.phase == "normal":
            # process data
            for e in range(self.size):
                if data[e] is not None:
                    self.data_list[e] = data[e]

            # bump iteration
            self.i += 1

            # next iteration
            if self.i < self.iterations:
                self.iterate()
            else:
                self.odd()

            return True
        elif self.phase == "odd":
            my_gap_start = self.rank+1
            j = 0
            for gdx in range(my_gap_start,my_gap_start+self.gap_size):
                idx = gdx % self.size
                gap_item = data[j]
                self.data_list[idx] = gap_item
                j += 1
            self.finish()
            return True
        else:
            Logger().warning("accept_msg in unkown phase: %s" % self.phase)

        return False

    def odd(self):
        if self._finished.is_set():
            return

        # Check if there are odd messages
        if not self.gap_size:
            return self.finish()

        self.phase = "odd"

        send_to = (self.rank + 2**self.i) % self.size
        self.recv_from = (self.rank - 2**self.i) % self.size

        # Get missing gap
        gap_start = send_to+1
        gap = self.data_list[gap_start:gap_start+self.gap_size]
        # Check if the gap wraps around
        gap_wrap = self.gap_size - len(gap)
        if gap_wrap:
            gap = gap+self.data_list[0:gap_wrap]

        s_handle = self.communicator._isend(gap, send_to, constants.TAG_ALLGATHER)

    def finish(self):
        self.data = self.data_list
        self._finished.set()

    def _get_data(self):
        return self.data

class TreeGather(BaseCollectiveRequest):
    """
    This is a generic gather request using different tree structures. It is
    simple to use this as it is a matter of extending, adding the wanted
    topology tree and then implementing the accept() class method. See the below
    defined classes for examples.
    """
    def __init__(self, communicator, data=None, root=0):
        super(TreeGather, self).__init__()

        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        self.data = [None] * self.size
        self.data[self.rank] = data

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant gather without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()
        self.missing_children = copy.copy(self.children)

        # We forward up the tree unless we have to wait for children
        if not self.children:
            self.send_parent()

    def send_parent(self):
        # Send data to the parent (if any)
        if (not self._finished.is_set()) and self.parent is not None:
            self.communicator._isend(self.data, self.parent, tag=constants.TAG_GATHER)

        self._finished.set()

    def accept_msg(self, rank, data):
        if self._finished.is_set() or rank not in self.missing_children:
            return False

        self.missing_children.remove(rank)

        for i in range(len(data)):
            item = data[i]
            if item is not None:
                self.data[i] = item

        if not self.missing_children:
            self.send_parent()

        return True

    def _get_data(self):
        if self.root == self.rank:
            return self.data
        else:
            return None

class FlatTreeGather(TreeGather):
    """
    Performs a flat tree broadcast (root sends to all other). This algorithm
    should only be performed when the size is 10 or smaller.
    """
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(cls, communicator, *args, **kwargs):

        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.FlatTree(communicator, root=kwargs['root'])

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class BinomialTreeGather(TreeGather):
    ACCEPT_SIZE_LIMIT = 50

    @classmethod
    def accept(cls, communicator, *args, **kwargs):

        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.BinomialTree(communicator, root=kwargs['root'])

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class StaticFanoutTreeGather(TreeGather):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        obj = cls(communicator, *args, **kwargs)

        topology = tree.BinomialTree(communicator, root=kwargs['root'])

        # Insert the toplogy as a smart trick
        obj.topology = topology

        return obj
