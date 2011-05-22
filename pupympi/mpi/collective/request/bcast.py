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
            self.send_to_children(False)
            # Mark that we are done with this request from a local perspective
            self._finished.set()

    def accept_msg(self, rank, raw_data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank == self.parent:
            self.data = raw_data
            # Pass it on to children if we have any
            if self.children:
                self.send_to_children()
            # DEBUG
            #Logger().debug("--accept_msg to:%i from:%i children:%s" % (self.rank, rank, self.children) )

            # Mark that we are done with this request from a local perspective
            self._finished.set()
            return True

        return False

    def send_to_children(self, transit=True):
        """
        Nice wrapper around the direct send call
        
        Transit flag means the sending node is just a transit node for data, ie. the data is already serialized
        """
        self.communicator._direct_send(self.data, receivers=self.children, tag=constants.TAG_BCAST, serialized=transit)
        # DEBUG
        Logger().debug("--sent to %s" % self.children)
        

    def _get_data(self):        
        # For root the data is not serialized
        if self.parent is None:
            return self.data
        else:
            import pickle
            return pickle.loads(self.data)

class FlatTreeBCast(FlatTreeAccepter, TreeBCast):
    pass

class BinomialTreeBCast(BinomialTreeAccepter, TreeBCast):
    pass

class StaticFanoutTreeBCast(StaticFanoutTreeAccepter, TreeBCast):
    pass

class RingBCast(BaseCollectiveRequest):
    """
    Implementation of the bcast collective operations by traversing
    the communicators participants in a ring. This will introduce
    more latency in the operations, but also result in less overhead
    and lower memory footprint.
    """
    def __init__(self, communicator, data=None, root=0):
        super(RingBCast, self).__init__(communicator)
        
        self.communicator = communicator
        self.rank = self.communicator.comm_group.rank()
        self.size = self.communicator.comm_group.size()
        
        self.root = root
        self.data = data
        
        self.next = (self.rank +1) % self.size
        self.previous = (self.rank -1) % self.size
        
    def start(self):
        if self.rank == self.root:
            self.forward()
            
    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False
        
        if rank != self.previous:
            return False
        
        self.data = data
        
        self.forward()
        
        return True
                
    def forward(self):
        self.communicator._isend(self.data, self.next, tag=constants.TAG_BCAST)
        self._finished.set()
        
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        # Debug for testing. This will always accept, which makes it 
        # quite easy to test.
        return cls(communicator, *args, **kwargs)
