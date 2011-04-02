from mpi.collective.request import BaseCollectiveRequest, FlatTreeAccepter, BinomialTreeAccepter, StaticFanoutTreeAccepter
from mpi import constants
from mpi.logger import Logger
from mpi.topology import tree

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
        for i in xrange(self.iterations):
            self.send_to.append( (2**i+self.rank) % self.size )
            self.recv_from.append( (self.rank - (2**i)) % self.size )
        
        # TODO: Fill in gap too
        # Filling gap
        if self.gap_size:            
            # Calculate rank for receive and send (own rank offset by half of next power of two)
            self.send_to.append( (self.rank + 2**self.iterations) % self.size )
            self.recv_from.append( (self.rank - 2**self.iterations) % self.size )
            
            
            # TODO: Reinstate below to limit the size of the gap transmission to what is actually missing
            ## Get missing gap
            #gap_start = self.send_to+1
            #gap = data_list[gap_start:gap_start+gap_size]
            ## Check if the gap wraps around
            #gap_wrap = gap_size - len(gap)
            #if gap_wrap:
            #    gap = gap+data_list[0:gap_wrap]
            #    
            ## Exchange gaps
            #r_handle = self.communicator.irecv(recv_from, self.tag)
            #s_handle = self.communicator.isend(gap, send_to, self.tag)
            #res = self.communicator.waitall([r_handle,s_handle])
            #
            ## Fill out gap
            #my_gap_start = self.rank+1
            #received = res[0]
            #j = 0
            #for gdx in range(my_gap_start,my_gap_start+gap_size):
            #    idx = gdx % size
            #    gap_item = received[j]
            #    data_list[idx] = gap_item
            #    j += 1
                
        # Start by sending the message for iteration 0
        self.communicator._isend(self.data_list, self.send_to[0], constants.TAG_ALLGATHER)
        
        # Mark send communication as done for iteration 0
        self.send_to[0] = None
        # DEBUG
        #Logger().debug("rank:%i started rf:%s st:%s" % (self.rank, self.recv_from, self.send_to))
    

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
                # DEBUG
                #Logger().debug("rank:%i SENDING iteration:%i, send_to:%s, data:%s" % (self.rank,iteration,self.send_to, self.data_list))
                self.communicator._isend(self.data_list, r, constants.TAG_ALLGATHER)
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

        # We forward up the tree unless we have to wait for children
        if not self.children:
            self.send_parent()

    def send_parent(self):
        # Send data to the parent (if any)
        if (not self._finished.is_set()) and self.parent is not None:
            self.communicator._isend(self.data, self.parent, tag=constants.TAG_GATHER)

        self._finished.set()

    def accept_msg(self, rank, data):
        if self._finished.is_set() or rank not in self.missing_children:
            return False

        self.missing_children.remove(rank)

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

class FlatTreeGather(FlatTreeAccepter, TreeGather):
    pass

class BinomialTreeGather(BinomialTreeAccepter, TreeGather):
    pass

class StaticFanoutTreeGather(StaticFanoutTreeAccepter, TreeGather):
    pass
