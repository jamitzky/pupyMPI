from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger

from mpi.topology import tree

import copy

class TreeAllReduce(BaseCollectiveRequest):
    def __init__(self, communicator, data, operation, tag=constants.TAG_ALLREDUCE):
        super(TreeAllReduce, self).__init__()

        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.root = 0
        self.tag = tag

        self.operation = operation
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
                    self.data = {self.rank : self.operation(self.received_data.values())}
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
        if self.partial:
            return self.data[self.root]
        else:
            keys = self.data.keys()
            keys.sort()
            new_data = []
            for k in keys:
                new_data.append( self.data[k] )

            return self.operation(new_data)

    def to_children(self):
        for child in self.children:
            self.communicator._isend(self.data, child, tag=self.tag)

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

class FlatTreeAllReduce(TreeAllReduce):
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)
            topology = tree.FlatTree(communicator, root=0)

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class BinomialTreeAllReduce(TreeAllReduce):
    ACCEPT_SIZE_LIMIT = 50

    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.BinomialTree(communicator, root=0)

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class StaticTreeAllReduce(TreeAllReduce):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        obj = cls(communicator, *args, **kwargs)

        topology = tree.BinomialTree(communicator, root=0)

        # Insert the toplogy as a smart trick
        obj.topology = topology

        return obj

# ------------------------ reduce operation below ------------------------
class TreeReduce(BaseCollectiveRequest):
    def __init__(self, communicator, data, operation, root=0):
        super(TreeReduce, self).__init__()

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
                self.data = {self.rank : self.operation(self.received_data.values())}
            else:
                self.data = self.received_data

            # forward to the parent.
            self.to_parent()
        return True

    def _get_data(self):
        if self.rank == self.root:
            if self.partial:
                return self.data[self.rank]
            else:
                keys = self.data.keys()
                keys.sort()
                new_data = []
                for k in keys:
                    new_data.append( self.data[k] )

                return self.operation(new_data)
        else:
            return None

    def to_parent(self):
        # Send self.data to the parent.
        if self.parent is not None:
            self.communicator._isend(self.data, self.parent, tag=constants.TAG_REDUCE)

        self._finished.set()

class FlatTreeReduce(TreeReduce):
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

class BinomialTreeReduce(TreeReduce):
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

class StaticTreeReduce(TreeReduce):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        obj = cls(communicator, *args, **kwargs)

        topology = tree.BinomialTree(communicator, root=kwargs['root'])

        # Insert the toplogy as a smart trick
        obj.topology = topology
        return obj

# ------------------------ scan operation below ------------------------
class TreeScan(TreeAllReduce):
    def __init__(self, communicator, data, operation):
        self.partial = False
        super(TreeScan, self).__init__(communicator, data, operation, tag=constants.TAG_SCAN)

    def clean_data(self):
        keys = self.data.keys()
        keys.sort()

        new_data = {}
        so_far = []

        for rank in keys:
            data = self.data[rank]
            so_far.append(data)

            reduced = self.operation(so_far)
            new_data[rank] = reduced

        self.data = new_data

    def _get_data(self):
        return self.data[self.rank]


class FlatTreeScan(TreeScan):
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)
            topology = tree.FlatTree(communicator, root=0)

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class BinomialTreeScan(TreeScan):
    ACCEPT_SIZE_LIMIT = 50

    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            obj = cls(communicator, *args, **kwargs)

            topology = tree.BinomialTree(communicator, root=0)

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class StaticFanoutTreeScan(TreeScan):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        obj = cls(communicator, *args, **kwargs)

        topology = tree.BinomialTree(communicator, root=0)

        # Insert the toplogy as a smart trick
        obj.topology = topology

        return obj
