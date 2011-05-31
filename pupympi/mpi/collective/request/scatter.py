from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi import constants
import mpi.network.utils as utils

from mpi.logger import Logger

from mpi.topology import tree

class TreeScatter(BaseCollectiveRequest):
    """
    Generic scatter valid for all types
    """
    def __init__(self, communicator, data=None, root=0):
        super(TreeScatter, self).__init__()

        self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        # Slice the data.
        if self.root == self.rank:
            chunk_size = len(data) / self.size
            self.data = [data[r*chunk_size:(r+1)*chunk_size] for r in range(self.size) ]

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cannot broadcast without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        if self.parent is None:
            self.send_to_children()
            
    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False
        
        if rank == self.parent:
            self.msg_type = msg_type # Note msg_type since it determines how to send down
            self.data = utils.deserialize_message(raw_data, msg_type)
            self.send_to_children()
            return True

        return False

    def send_to_children(self, transit=True):
        for child in self.children:
            desc = self.topology.descendants(child)
            data = [None] * self.size
            data[child] = self.data[child]
            for r in desc:
                data[r] = self.data[r]
            self.communicator._isend(data, child, tag=constants.TAG_SCATTER)

        self._finished.set()

    def _get_data(self):
        # We only need our own data
        return self.data[self.rank]


class TreeScatterPickless(BaseCollectiveRequest):
    """
    Scatter taking advantage of bytearrays and ndarrays
    
    ISSUE: Multi-dimensional ndarrays are not handled properly yet
    """
    def __init__(self, communicator, data=None, root=0):
        super(TreeScatterPickless, self).__init__()

        self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        
        self.msg_type = None

        # Slice the data
        if self.root == self.rank:
            chunk_size = len(data) / self.size
            self.data = [data[r*chunk_size:(r+1)*chunk_size] for r in range(self.size) ]
        
        #Logger().debug("rank:%i initialized data:%s from:%s" % (self.rank, self.data, data) )

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cannot broadcast without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        if self.parent is None:
            self.send_to_children()
            
    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False
        
        #Logger().debug("rank:%i accepts raw data:%s" % (self.rank, raw_data) )
        
        if rank == self.parent:
            self.msg_type = msg_type # Note msg_type since it determines how to send down
            
            #if self.msg_type == constants.CMD_USER:
            #else:
            self.data = utils.deserialize_message(raw_data, msg_type)
            #Logger().debug("rank:%i got data:%s" % (self.rank, self.data) )
            self.send_to_children()
            return True

        return False

    def send_to_children(self, transit=True):
        for child in self.children:
            desc = self.topology.descendants(child)
            data = [None] * self.size
            data[child] = self.data[child]
            for r in desc:
                data[r] = self.data[r]

            #Logger().debug("send to child:%s desc:%s data:%s" % (child, desc, data) )
            
            self.communicator._isend(data, child, tag=constants.TAG_SCATTER)

        self._finished.set()

    def _get_data(self):
        Logger().debug("rank:%i GET data:%s" % (self.rank, self.data) )
        # We only need our own data
        return self.data[self.rank]

class FlatTreeScatter(FlatTreeAccepter, TreeScatter): 
    pass

class BinomialTreeScatter(BinomialTreeAccepter, TreeScatter):
    pass

class BinomialTreeScatterPickless(BinomialTreeAccepter, TreeScatter):
    pass

#class BinomialTreeScatterPickless(BinomialTreeAccepter, TreeScatterPickless):
#    pass


class StaticFanoutTreeScatter(StaticFanoutTreeAccepter, TreeScatter):
    pass
