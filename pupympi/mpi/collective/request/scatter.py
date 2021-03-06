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
        super(TreeScatter, self).__init__(communicator, data=data, root=root)

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
            self.isend(data, child, tag=constants.TAG_SCATTER)

        self.done()

    def _get_data(self):
        # We only need our own data
        return self.data[self.rank]

class TreeScatterPickless(BaseCollectiveRequest):
    """
    Scatter taking advantage of bytearrays and ndarrays

    ISSUES:
    - Still no switching with regular TreeScatter
    """
    def __init__(self, communicator, data=None, root=0):
        super(TreeScatterPickless, self).__init__(communicator, data=data, root=root)
        
        self.root = root
        self.communicator = communicator
        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()
        self.msg_type = None
        
        # Serialize the data
        if self.root == self.rank:
            # TODO: This is done from the start but maybe we want to hold off until later, if so root could skip the (de)serialization to self
            self.data,self.msg_type,length = utils.serialize_message(data, recipients=self.size)
            
            # Multidimensional arrays require a bit more care
            self.shapelen = self.msg_type / 1000 # the number of shapebytes hide in the upper decimals of cmd
            if self.shapelen:
                self.shapebytes = self.data[0]
                self.shape = utils.get_shape(self.shapebytes)
                # for multidim the data will be in second position
                self.data = self.data[1]
            else:
                self.data = self.data[0]
                
            self.chunksize = (length-self.shapelen) / self.size # shapebytes are counted separately
            
        else:
            self.data = None
            self.shapelen = False

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
            # Multidimensional arrays have the number of shapebytes hiding in the upper decimals
            self.shapelen = msg_type / 1000
            # multidimensional array?
            if self.shapelen:
                self.shapebytes = raw_data[:self.shapelen]
                self.shape = utils.get_shape(self.shapebytes)
            
            self.data = raw_data
            
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

        shapeoffset = 0
        # non-root nodes need to set chunksize and have a shapeoffset since the shapebytes are included in self.data
        if self.parent is not None:
            # chunksize is always the data the node holds relative to how many nodes (including self) will share it
            self.chunksize = (len(self.data)  - self.shapelen) / len(all_ranks)            
            # TODO: len(all_ranks) should be calculated in advance based on tree generation
            shapeoffset = self.shapelen

        # Note the position of the node's own slice (only differs from 0 if involved in a root-swap)
        self.pos = rank_pos_map[self.rank]

        for child in self.children:
            desc = self.topology.descendants(child)
            all_ranks = [child]+desc # All the recipients of the message
            all_ranks.sort() # keep it sorted
            if self.shapelen:
                payloads = [self.shapebytes] # First payload to send is always shapebytes
            else:
                payloads = []
            for r in all_ranks:
                pos_r = rank_pos_map[r]
                begin = pos_r * (self.chunksize) + shapeoffset
                end = begin + (self.chunksize)
                payloads.append( self.data[begin:end] )

            p_length = self.shapelen + len(all_ranks)*self.chunksize # length af all payloads combined
            self.multisend(payloads, child, tag=constants.TAG_SCATTER, cmd=self.msg_type, payload_length=p_length)

        self.done()

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        """
        Accept as long as it is numpy array or bytearray
        """
        import numpy # FIXME: Move this import somewhere nice

        # NOTE: Maybe change the kwargs['data'] to kwargs.get('data',None) in case some silly bugger omits the named parameter
        if isinstance(kwargs['data'], numpy.ndarray) or isinstance(kwargs['data'],bytearray):
            obj = cls(communicator, *args, **kwargs)
            #Logger().debug("rank:%i ACCEPT with args:%s, kwargs:%s obj:%s cls:%s" % (communicator.rank(), args, kwargs, obj, cls))

            # Check if the topology is in the cache
            root = kwargs.get("root", 0)
            cache_idx = "tree_binomial_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                # TODO:
                # here the orthogonality of accepting on topology vs. accepting on data type or data size really kicks in
                # since the accept logic is coded only with communicator size in mind, it is hard to intersperse other accept conditions
                # For now we just assume that binomial tree is the way to go,that is we ignore communicator size
                # BUT when benchmarking we should have both the data type AND the communicator size considered before choosing a class
                topology = tree.BinomialTree(size=communicator.size(), rank=communicator.rank(), root=root)
                cache.set(cache_idx, topology)

            obj.topology = topology
            return obj

    def _get_data(self):
        if self.shapelen:
            # multidim
            if self.parent is None:
                # root
                begin = self.pos * self.chunksize
                end = begin + self.chunksize
                return utils.deserialize_message([self.shapebytes,self.data[begin:end]], self.msg_type)
            else:
                # others
                begin = self.pos * self.chunksize + self.shapelen
                end = begin + self.chunksize
                return utils.deserialize_message(self.shapebytes+self.data[begin:end], self.msg_type)
                
        else:
            # onedim
            begin = self.pos * self.chunksize
            end = begin + self.chunksize
            return utils.deserialize_message(self.data[begin:end], self.msg_type)


class FlatTreeScatter(FlatTreeAccepter, TreeScatter):
    pass

class BinomialTreeScatter(BinomialTreeAccepter, TreeScatter):
    pass

class BinomialTreeScatterPickless(TreeScatterPickless):
    pass

class StaticFanoutTreeScatter(StaticFanoutTreeAccepter, TreeScatter):
    pass
