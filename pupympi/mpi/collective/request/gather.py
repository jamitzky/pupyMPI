from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi import constants
from mpi.logger import Logger
from mpi.topology import tree
from mpi import utils

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
        # Data list to hold gathered result - indexed by rank
        self.data_list = [None] * self.size
        self.data_list[self.rank] = self.data # Fill in own value

        self.iterations = int(log(self.size, 2)) # How many iterations the algorithm will run, excluding gap-filling
        self.gap_size = self.size - 2**self.iterations # If size is not a power of 2 there will be a gap
        
        # Ranks to receive or send from for algorithm to complete
        # - indexed by the iteration in which the communication is to occur
        self.send_to = []
        self.recv_from = []
        self.send_ranges = [] # list of tuples of (range start, range end) where start may be larger than end, in the wrap-around case
        for i in xrange(self.iterations):
            self.send_to.append( (2**i+self.rank) % self.size )
            self.recv_from.append( (self.rank - (2**i)) % self.size )
            start = (self.rank - (2**i) + 1) % self.size
            self.send_ranges.append( (start,self.rank) )
        
        # Filling gap
        if self.gap_size:
            # Calculate rank for receive and send (own rank offset by half of next power of two)
            gap_send_to = (self.rank + 2**self.iterations) % self.size
            
            self.send_to.append( gap_send_to )
            self.recv_from.append( (self.rank - 2**self.iterations) % self.size )
            
            gap_start = (gap_send_to + 1) % self.size
            gap_end = (gap_start + self.gap_size) % self.size
            self.send_ranges.append( (gap_start, gap_end) )
            # DEBUG
            #Logger().debug("rank:%i gap_start:%i gap_end:%i" % (self.rank, gap_start, gap_end))
                
        # Start by sending the message for iteration 0
        self.communicator._isend(self.data_list, self.send_to[0], constants.TAG_ALLGATHER)
        
        # Mark send communication as done for iteration 0
        self.send_to[0] = None
    

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        """
        This implementation is so supreme that we accept problems of any sizes
        and layout. GO TEAM DISSEMINATION.
        """
        return cls(communicator, *args, **kwargs)

    def accept_msg(self, rank, data):
        """
        Check that the message is expected and send off messages as appropriate
        """
        if self._finished.is_set() or rank not in self.recv_from:
            Logger().debug("accept_msg BAIL finished_is_set:%s or rank:%i != self.recv_from:%s data was:%s" % (self._finished.is_set(), rank, self.recv_from,data))
            return False

        # Put valid data in proper place            
        for e in range(self.size):
            if data[e] is not None:
                self.data_list[e] = data[e]
            
        # Check if the accept puts the algorithm into next iteration
        iteration = 0
        blocked = False
        for i,r in enumerate(self.recv_from):
            if r == rank: # When we hit the rank we mark as having received
                self.recv_from[i] = None
                # If no blockers were found before, the next iteration can begin
                if not blocked:
                    iteration = i+1                
            elif r == None: # Nones means that we have already received that iteration
                if not blocked:
                    iteration = i+1                
            else: # If we hit any other rank it means we are still waiting for the receive belonging to that iteration
                if not blocked: # First one we hit takes precedence
                    iteration = i
                    blocked = True
        
        # DEBUG
        #Logger().debug("rank:%i RECV iteration:%i, recv_from:%s, r:%s" % (self.rank,iteration,self.recv_from, rank))

        # Check if the next iteration needs sending
        for i, r in enumerate(self.send_to):
            if i > iteration: # We should send only up to the iteration after the one found to have been completed
                break
            elif r != None:
                # Slice out the data that needs to be sent
                (start,end) = self.send_ranges[i]
                if end < start:
                    slice = self.data_list[:end+1] + [None]*(start-end-1) + self.data_list[start:]
                else:
                    slice = [None]*start + self.data_list[start:end+1] + [None]*(self.size - (end+1))

                # DEBUG
                #Logger().debug("rank:%i SENDING iteration:%i, send_to:%s, data:%s" % (self.rank,iteration,self.send_to, slice))
                
                self.communicator._isend(slice, r, constants.TAG_ALLGATHER)
                self.send_to[i] = None
                
        # Check if we are done
        #if iteration == self.iterations: # This check is not good enough for procs who receive out of order
        if set(self.recv_from+self.send_to) == set([None]):            
            self.finish()
        
        #Logger().debug("rank:%i ACCEPTED rf:%s st:%s" % (self.rank, self.recv_from, self.send_to))
        return True

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
    
    SETTINGS_PREFIX = "GATHER"
    
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
        #Logger().debug("No go away class!")
        # We forward up the tree unless we have to wait for children
        if not self.children:
            self.send_parent()

    def send_parent(self):        
        # Send data to the parent (if any)
        if (not self._finished.is_set()) and self.parent is not None:
            self.communicator._isend(self.data, self.parent, tag=constants.TAG_GATHER)            
        self._finished.set()

    def accept_msg(self, rank, raw_data, msg_type=None):
        if self._finished.is_set() or rank not in self.missing_children:
            return False

        self.missing_children.remove(rank)
        
        data = utils.deserialize_message(raw_data, msg_type)

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

class TreeGatherPickless(BaseCollectiveRequest):
    """
    This is a gather used when data should not be pickled and unpickled on its way
    up in the tree.
    
    A leaf sends its serialized payload to parent
    A middle node waits for payloads from all children, then payloads are sent in order of increasing rank, with one's own first (excluding root swap)
    Root waits for payloads from all children and the rearranges in rank order and deserializes
    
    All ranks are assumed to supply equally long arrays to the operation
    
    ISSUES:
    - Currently only ndarrays trigger the use of this class, eventually we'll want bytearrays too
    - Hardcoded with binomial tree since comm size is not taken into account
    """
    
    SETTINGS_PREFIX = "GATHERPL"
    
    def __init__(self, communicator, data=None, root=0):
        super(TreeGatherPickless, self).__init__()

        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        self.data = [None] * self.size
        self.data[self.rank],cmd = utils.serialize_message(data)
        self.msg_type = cmd
        self.chunksize = len(self.data[self.rank])
        
    def start(self):
        topology = getattr(self, "topology", None) # You should really set the topology.. please
        if not topology:
            raise Exception("Cant gather without a topology... do you expect me to randomly behave well? I REFUSE!!!")

        self.parent = topology.parent()
        self.children = topology.children()
        self.missing_children = copy.copy(self.children)
        #Logger().debug("NUMPY CLASS - rank:%i has children:%s" % (self.rank,self.children) )
        
        # We forward up the tree unless we have to wait for children
        if not self.children:
            self.send_parent()

    def send_parent(self):
        # Send data to the parent (if any)
        if (not self._finished.is_set()) and self.parent is not None:
            
            payloads = [d for d in self.data if d is not None] # Filter potential Nones away
            self.communicator._multisend(payloads, self.parent, tag=constants.TAG_GATHER, cmd=self.msg_type, payload_length=len(payloads)*self.chunksize )

        self._finished.set()

    def accept_msg(self, child_rank, raw_data, msg_type):
        if self._finished.is_set() or child_rank not in self.missing_children:
            return False
        
        self.missing_children.remove(child_rank)
        
        desc = self.topology.descendants(child_rank)
        all_ranks = [child_rank]+desc # All the ranks having a payload in this message
        all_ranks.sort() # keep it sorted
        # Map child/descendant ranks to position in raw_data
        #rank_pos_map = dict([(r,i) for i,r in enumerate(all_ranks)])

        # Store payloads in proper positions
        for i,r in enumerate(all_ranks):
            pos_r = i
            begin = pos_r * (self.chunksize)
            end = begin + (self.chunksize)
            
            self.data[r] = raw_data[begin:end]
        

        if not self.missing_children:
            self.send_parent()

        return True

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        """
        Accept as long as it is numpy data
        
        TODO: Needs to accept bytearrays also
        """
        import numpy # FIXME: Move this import somewhere nice
        
        # NOTE: Maybe change the kwargs['data'] to kwargs.get('data',None) in case some silly bugger omits the named parameter
        if isinstance(kwargs['data'], numpy.ndarray) or isinstance(kwargs['data'],bytearray):
            obj = cls(communicator, *args, **kwargs)
            
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
        if self.root == self.rank:
            # The root deserializes all payloads
            return [ utils.deserialize_message(self.data[r], self.msg_type) for r in range(self.size) ]
        else:
            return None

class FlatTreeGather(FlatTreeAccepter, TreeGather):
    pass

class BinomialTreeGatherPickless(TreeGatherPickless):
    pass

class BinomialTreeGather(BinomialTreeAccepter, TreeGather):
    pass

class StaticFanoutTreeGather(StaticFanoutTreeAccepter, TreeGather):
    pass
