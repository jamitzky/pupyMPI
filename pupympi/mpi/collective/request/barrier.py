from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger

from mpi.topology import tree

import copy

class TreeBarrier(BaseCollectiveRequest):
    """
    This is a generic barrier request using different tree structures. It is
    simple to use this as it is a matter of extending, adding the wanted
    topology tree and then implementing the accept() class method. See the below
    defined classes for examples.

    The tree barrier is different from most other collective request as every
    rank must wait until they receive from their parent, send to their children
    and receive from their children once again.
    """
    def __init__(self, communicator):
        super(TreeBarrier, self).__init__()

        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.data = None

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant barrier without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        self.missing_children = copy.copy(self.children)
        self.wait_parent = False

        # Send a barrier tag to the parent if there are no children (and therefore
        # nothing to wait for)
        if not self.children: # leaf
            self.send_parent()

    def send_parent(self):
        # Send a barrier token upwards.
        self.communicator._isend(None, self.parent, tag=constants.TAG_BARRIER)
        self.wait_parent = True

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if self.wait_parent:
            if rank != self.parent:
                return False

            # We have now received messsage from our parent on the way
            # downwards in the tree. We forward the message to the children
            # and exit from the barrier.
            self.send_children()
            return True
        else:
            # If we need to hear from any of our children, we only accept messages
            # from those.
            if self.missing_children:
                if rank not in self.missing_children:
                    return False

                self.missing_children.remove(rank)

                if not self.missing_children:
                    # We received from all the necessary children. We send to the
                    # parent.
                    if self.parent is not None:
                        self.send_parent()
                        self.wait_parent = True
                    else:
                        # Send to the children.
                        self.send_children()
                return True

            return False

    def send_children(self):
        for child in self.children:
            self.communicator._isend(None, child, tag=constants.TAG_BARRIER)

        # We have now sent to every child. This mean that we can exit from
        # the barrier.
        self._finished.set()

    def _get_data(self):
        return self.data

class FlatTreeBarrier(TreeBarrier):
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

            topology = tree.FlatTree(communicator, root=0)

            # Insert the toplogy as a smart trick
            obj.topology = topology

            return obj

class BinomialTreeBarrier(TreeBarrier):
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

class StaticFanoutTreeBarrier(TreeBarrier):
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        obj = cls(communicator, *args, **kwargs)

        topology = tree.BinomialTree(communicator, root=0)

        # Insert the toplogy as a smart trick
        obj.topology = topology

        return obj
