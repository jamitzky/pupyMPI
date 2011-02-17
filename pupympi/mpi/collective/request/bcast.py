from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi import constants
from mpi.logger import Logger

from mpi.topology import tree

class TreeBCast(BaseCollectiveRequest):
    """
    This is a generic broadcast request using different tree structures. It is
    simple to use this as it is a matter of extending, adding the wanted
    topology tree and then implementing the accept() class method. See the below
    defined classes for examples.

    The functionality is also pretty simple. Each request looks at the parent
    in the topology. If there is none, we must be the root, so we sends data
    to each child. If - on the other hand - there is a parent, we wait for
    a message from that rank and send to our own children.
    """
    
    SETTINGS_PREFIX = "BCAST"
    
    def __init__(self, communicator, data=None, root=0):
        super(TreeBCast, self).__init__()

        self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant broadcast without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        if self.parent is None:
            # we're the root.. let us send the data to each child
            self.send_to_children()

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank == self.parent:
            self.data = data
            self.send_to_children()
            return True

        return False

    def send_to_children(self):
        self.communicator._direct_send(self.data, receivers=self.children, tag=constants.TAG_BCAST)
        self._finished.set()

    def _get_data(self):
        return self.data

class FlatTreeBCast(FlatTreeAccepter, TreeBCast):
    pass

class BinomialTreeBCast(BinomialTreeAccepter, TreeBCast):
    pass

class StaticFanoutTreeBCast(StaticFanoutTreeAccepter, TreeBCast):
    pass