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
            # we're the root.. let us send the data to each child
            self.send_to_children()

    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank == self.parent:
            self.data = utils.deserialize_message(raw_data, msg_type)
            self.send_to_children()
            return True

        return False

    def send_to_children(self):
        for child in self.children:
            # Create new data. This will not include a lot of data copies
            # as we are only making references in the new list.
            data = [None] * self.size
            data[child] = self.data[child]            
            desc = self.topology.descendants()
            for r in range(self.size):
                if r == child or r in desc[child]:
                    data[r] = self.data[r]
            #Logger().debug("children:%s desc:%s values:%s" % (self.children, desc, desc.values()) )
            self.communicator._isend(self.data, child, tag=constants.TAG_SCATTER)

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

    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cannot broadcast without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()

        if self.parent is None:
            self.send_to_children()
            ## we're the root.. let us send the data to each child
            #
            ## note msg type for later
            #payload,msg_type = utils.serialize_message(self.data)
            ##msg = utils.prepare_message(self.data, self.rank, cmd=0, tag=constants.TAG_SCATTER, ack=False, comm_id=self.communicator.id, is_serialized=False)
            #
            #for child in self.children:
            #    
            #    data = [None] * self.size
            #    data[child] = self.data[child]            
            #    desc = self.topology.descendants()
            #    for r in range(self.size):
            #        if r == child or r in desc[child]:
            #            data[r] = self.data[r]
            #    Logger().debug("children:%s desc:%s values:%s" % (self.children, desc, desc.values()) )
            #    self.communicator._isend(self.data, child, tag=constants.TAG_SCATTER)
            #
            #self._finished.set()
            
    def accept_msg(self, rank, raw_data, msg_type):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank == self.parent:
            self.msg_type = msg_type # Note msg_type since it determines how to send down
            
            #if self.msg_type == constants.CMD_USER:
            #else:
            self.data = utils.deserialize_message(raw_data, msg_type)
            self.send_to_children()
            return True

        return False

    def send_to_children(self, transit=True):
        desc = self.topology.descendants()
        
        for child in self.children:
            data = [None] * self.size
            
            ranks = desc[child].append(child)
            data[child] = self.data[child]            
            desc = self.topology.descendants()
            for r in range(self.size):
                if r == child or r in desc[child]:
                    data[r] = self.data[r]
            Logger().debug("child:%s desc:%s subnodes:%s" % (child, desc, ranks) )
                    
            #Logger().debug("children:%s desc:%s values:%s" % (self.children, desc, desc.values()) )            
            #Logger().debug("children:%s desc:%s values:%s flat:%s" % (self.children, desc, desc.values(), [ r for sublist in desc.values() for r in sublist ]) )
             
            self.communicator._isend(self.data, child, tag=constants.TAG_SCATTER)
        #for child in self.children:
        #    # Create new data. This will not include a lot of data copies
        #    # as we are only making references in the new list.
        #    data = [None] * self.size
        #    data[child] = self.data[child]            
        #    desc = self.topology.descendants()
        #    for r in range(self.size):
        #        if r == child or r in desc[child]:
        #            data[r] = self.data[r]
        #    Logger().debug("children:%s desc:%s values:%s" % (self.children, desc, desc.values()) )
        #    #Logger().debug("children:%s desc:%s values:%s flat:%s" % (self.children, desc, desc.values(), [ r for sublist in desc.values() for r in sublist ]) )
        #     
        #    self.communicator._isend(self.data, child, tag=constants.TAG_SCATTER)

        self._finished.set()

    def _get_data(self):
        # We only need our own data
        return self.data[self.rank]

class FlatTreeScatter(FlatTreeAccepter, TreeScatter): 
    pass

class BinomialTreeScatter(BinomialTreeAccepter, TreeScatter):
    pass

class BinomialTreeScatterPickless(BinomialTreeAccepter, TreeScatterPickless):
    pass

class StaticFanoutTreeScatter(StaticFanoutTreeAccepter, TreeScatter):
    pass
