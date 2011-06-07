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

        #self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        
        self.msg_type = None
        
        # Serialize the data
        if self.root == self.rank:
            # TODO: This is done from the start but maybe we want to hold off until later
            self.data,cmd = utils.serialize_message(data)
            self.msg_type = cmd
            #chunk_size = len(data) / self.size
            #self.data = [data[r*chunk_size:(r+1)*chunk_size] for r in range(self.size) ]
            Logger().debug("RANK:%i len:%i cmd:%s" % (self.rank,len(self.data), cmd) )
            #Logger().debug("RANK:%i len:%i serialized:%s cmd:%s" % (self.rank,len(self.data), self.data, cmd) )
        else:
            self.data = data
        
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
        
        #Logger().debug("rank:%i accepts raw data:%s of len:%i msg_type:%s" % (self.rank, raw_data, len(raw_data), msg_type) )
        
        if rank == self.parent:
            self.msg_type = msg_type # Note msg_type since it determines how to send down
            
            #if self.msg_type == constants.CMD_USER:
            #else:
            self.data = raw_data
            #Logger().debug("rank:%i got data:%s" % (self.rank, self.data) )
            self.send_to_children()
            return True

        return False

    def send_to_children(self, transit=True):
        """
        Send appropriate data to all children including payloads for descendants
        
        NOTE: The first part of this function deals with setting attributes that
              are also used elsewhere. It could be refactored out but is is a
              requirement that data must be present at call time.
        """
        # Map child/descendant rank to position in self.data        
        all_ranks = [self.rank] + self.children
        for child in self.children:
            all_ranks.extend( self.topology.descendants(child) )
        all_ranks.sort()
        rank_pos_map = dict([(r,i) for i,r in enumerate(all_ranks)])
        
        # chunksize is always the data the node holds relative to how many nodes (including self) will share it
        self.chunksize = len(self.data) / len(all_ranks) # should be calculated in advance based on tree generation
        # Note the position of the node's own slice (only differ from 0 if involved in a root-swap)
        self.pos = rank_pos_map[self.rank]

        for child in self.children:
            desc = self.topology.descendants(child)
            
            #Logger().debug("rank%i has child:%s desc:%s" % (self.rank, child, desc) )            
            #data = [None] * self.size            
            #data[child] = self.data[child]
            
            payloads = []
            
            all_ranks = [child]+desc
            for r in all_ranks:
                pos_r = rank_pos_map[r]
                begin = pos_r * (self.chunksize)
                end = (pos_r+1) * (self.chunksize)
                #Logger().debug("descendant:%i has pos:%i and gets begin:%i end:%i" % (r, pos_r, begin, end) )
                try:                    
                    payloads.append( self.data[begin:end] )
                except Exception as e:
                    Logger().debug("rank%i has payloads:%s self.data:%s index(rank):%i of:%s" % (self.rank, payloads, self.data, r, desc) )
                    raise e

            p_length = len(all_ranks)*self.chunksize # length af all payloads combined

            #Logger().debug("send to child:%s payloads:%s of len:%i" % (child, payloads, len(payloads[0]) ))
            self.communicator._multisend(payloads, child, tag=constants.TAG_SCATTER, cmd=self.msg_type, payload_length=p_length)

        self._finished.set()

    def _get_data(self):
        #Logger().debug("rank:%i GET msg_type:%s chunksize:%s" % (self.rank, self.msg_type, self.chunksize) )
        begin = self.pos * self.chunksize
        end = begin + self.chunksize
        return utils.deserialize_message(self.data[begin:end], self.msg_type)
        

class FlatTreeScatter(FlatTreeAccepter, TreeScatter): 
    pass

class BinomialTreeScatter(BinomialTreeAccepter, TreeScatter):
    pass

class BinomialTreeScatterPickless(BinomialTreeAccepter, TreeScatterPickless):
    pass

class StaticFanoutTreeScatter(StaticFanoutTreeAccepter, TreeScatter):
    pass
