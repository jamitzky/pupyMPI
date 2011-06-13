from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
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

    SETTINGS_PREFIX = "BARRIER"

    def __init__(self, communicator):
        super(TreeBarrier, self).__init__(communicator)

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
        self.send(None, self.parent, tag=constants.TAG_BARRIER)
        self.wait_parent = True

    def accept_msg(self, rank, data, msg_type=None):
        # We do not care about the msg_type as the barrier call does not include
        # any data.

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
        self.direct_send(self.data, receivers=self.children, tag=constants.TAG_BARRIER, serialized=False)
        self._finished.set()

    def _get_data(self):
        return self.data

class FlatTreeBarrier(FlatTreeAccepter, TreeBarrier):
    pass

class BinomialTreeBarrier(BinomialTreeAccepter, TreeBarrier):
    pass

class StaticFanoutTreeBarrier(StaticFanoutTreeAccepter, TreeBarrier):
    pass

class RingBarrier(BaseCollectiveRequest):
    """
    Implementation of the barrier call by traversing the communicator
    participants in a ring. This will introduce more latency in the
    operation, but also result in less peak overhead / overload.
    """
    def __init__(self, communicator):
        super(RingBarrier, self).__init__(communicator)

        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        self.next = (self.rank +1) % self.size
        self.previous = (self.rank -1) % self.size

        # The number of messages to receive before the request is
        # allowed to finish.
        self.msg_count = 2

    def start(self):
        # Rank 0 is the root and will start the ring
        if self.rank == 0:

            # The root do not need to recieve the first message, so the
            # number of messages is just 1.
            self.msg_count = 1
            self.send_next()

    def accept_msg(self, rank, data, msg_type=None):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank != self.previous:
            return False

        if self.msg_count <= 0:
            return False

        self.msg_count -= 1

        # We have received from the rank before us, so we forward
        # the token to the next participant.
        self.send_next()

        # If we do not need to receive any more messages simply
        # set the finished flag.
        if self.msg_count == 0:
            self._finished.set()

        return True

    def send_next(self):
        self.isend(None, self.next, tag=constants.TAG_BARRIER)

    def send_previous(self):
        self.isend(None, self.previous, tag=constants.TAG_BARRIER)

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        # Debug for testing. This will always accept, which makes it
        # quite easy to test.
        return cls(communicator)
