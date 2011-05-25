"""
Test of different implementations of tree topologies
"""


class Tree(object):
    def __init__(self, root=0, size=1, rank=0):
        """
        Creating the topology.
        """
        #self.communicator = communicator
        #self.rank = communicator.comm_group.rank()
        #self.size = communicator.comm_group.size()
        self.size = size
        self.root = root
        self.rank = rank

        self.children = []
        self.parent = None
        self.descendants = {}

        # Generate the tree if there is a bound function with the
        # proper name
        self.tree = None
        generator = getattr(self, "generate_tree", None)
        if generator:
            self.tree = generator()
            
    def generate_tree(self):

        def node_create(rank):
            return {
              'rank' : rank,
              'children' : [],
            }
        """            
        If
        a) Every node can send one copy of the message to another rank in one iteration
        b) No node but the root can send before receiving from another node (a parent)
        
        The maximum depth d of the binomial tree is 
        
        Then a message is propagated through a tree of 2^i nodes in i iterations
       
        A node with rank r receives the message from its parent in iteration i
        where 2^(i-1) <= r < 2^i
        
        In iteration i a node with rank r sends to the receiver with rank n
        where n = 2^i + r
        
        A node with rank r in a tree of size s has the parent p
        where ???        
        """
        r = self.rank
        s = self.size
        
        # What is the final iteration
        import math        
        i_final = math.ceil(math.log(s,2))
        
        # In which iteration does the rank receive from parent
        i_start = 0
        while 2**i_start <= r:
            i_start += 1
            
        # What is the parent rank
        p = r - 2**(i_start-1)
            
        # What are the rank's children
        children = []
        i = i_start
        while i < i_final:
            r_child = 2**i + r
            if r_child < s:
                children.append(r_child)
            else:
                break
            i += 1
            
        # What are the ranks descendants
        
        
        
        print "for a tree of size:%i rank %i receives from parent:%i in iteration %i final_i:%i children:%s" % (self.size, r, p, i_start, i_final, children)

    def parent(self):
        """
        Returning the rank of the parent, None if the rank is the root of the
        tree.
        """
        return self._parent

    def children(self):
        """
        Return a list of children ranks. If called on a leaf-node the list
        will be empty.

        Different tree topologies might return list with different length. For
        example a binary tree will return a list of length 0, 1 or 2. A binomial
        tree can send anywhere between 0 l where the size of the tree is fab(l).
        """
        return self._children

    def descendants(self):
        """
        There are never any descendants
        """
        return self._descendants
    
for ra in range(19):
    #t = Tree(root=0,size=16, rank=ra)
    t = Tree(root=0,size=22, rank=ra)

