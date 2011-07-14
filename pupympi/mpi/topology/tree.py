"""
Contains different tree topologies. See the :func:`Tree` abstract topology for
the generic API available on all tree topologies. Each implementation can offer
other elements / functions, but the basic API **must** be implemented.
"""
from mpi.logger import Logger
import math

class Tree(object):
    def __init__(self, size=0, rank=0, root=0):
        """
        Creating the topology.
        """
        self.rank = rank
        self.size = size
        self.root = root

        # Placeholder objects. Each tree must fill these during generation
        self._parent = None
        self.child_ranks = [] # shorthand, just the ranks
        self._children = {} # { child rank : {'descendants : <int list>, 'iteration' : i } # iteration is the 'turn' in which the node would receive a message from root

        # Generate the tree if there is a bound function with the
        # proper name
        generator = getattr(self, "generate_tree", None)
        if generator:
            generator()

    def parent(self):
        """
        Returning the rank of the parent, None if the rank is the root of the
        tree.
        """
        if self.rank == self.root:
            return None
        else:
            return self._parent

    def children(self):
        """
        Return a list of children ranks. If called on a leaf-node the list
        will be empty.
        """
        return self.child_ranks

    def descendants(self, child_rank):
        """
        return the descendants of a given rank
        """
        return self._children[child_rank]['descendants']


class FlatTree(Tree):
    """
    Implements a flat free:
        -> Maximum height is 2 (the root and everything else).
        -> The root has size-1 fanout.
        -> None other than the root has any children.
    """
    def generate_tree(self):
        if self.rank == self.root:
            self._parent = None
            self.child_ranks = range(self.size)
            self.child_ranks.remove(self.rank) # All but own rank
            for i, rank in enumerate(self.child_ranks):
                self._children[rank] = {'descendants' : [], 'iteration' : i+1}
        else:
            self._parent = self.root
            self.child_ranks = []
            self._children = {}

class BinomialTree(Tree):
    def find_substitute_rank(self):
        # We use a substitute for our rank as we might have a reordering involved.
        if self.rank == 0 and self.root != 0:
            r = self.root  # Fake being a lower rank
        elif self.rank == self.root:
            r = 0 # Fake being root
        else:
            r = self.rank # Be yourself

        return r

    def generate_tree(self):
        """
        If
        a) Every node can send one copy of the message to another rank in one iteration
        b) No node but the root can send before receiving from another node (a parent)

        Then a message is propagated through a tree of 2^i nodes in i iterations

        A node with rank r receives the message from its parent in iteration i
        where 2^(i-1) <= r < 2^i

        In iteration i a node with rank r sends to the receiver with rank n
        where n = 2^i + r

        A node with rank r in a tree of size s has the parent p
        where p = r - 2**(i_start-1)

        children = { rank: { 'descendants': [d1,d2,...], 'start_iteration': i,  }, ... }
        """
        r = self.find_substitute_rank()
        s = self.size

        # What is the final iteration
        import math
        i_final = int(math.ceil(math.log(s,2)))

        # In which iteration does the rank receive from parent
        try:
            i_start = int(math.floor(math.log(r,2)) + 1)
        except ValueError as e:
            # Taking math.log of 0 raises ValueError: math domain error
            i_start = 0

        # What is the parent rank
        self._parent = int(r - 2**(i_start-1))

        # TODO: There are some optimizations possible in the following loops
        # What are the rank's children and each child's descendants
        i = i_start
        while i < i_final:
            r_child = 2**i + r
            if r_child < s:
                self.child_ranks.append(r_child)
                # Calculate descendants of the child
                desc = [r_child]
                i_future = i+1
                while i_future < i_final:
                    new_desc = []
                    for d in desc:
                        new_desc.append(2**i_future + d)
                    desc.extend(new_desc)
                    i_future += 1

                # Weed out own rank and ranks that are larger than max rank
                desc = [ dr for dr in desc[1:] if dr < s ]

                self._children[r_child] = {'descendants' : desc, 'start_iteration' : i}


            else:
                break
            i += 1

        # Now swap if needed
        self._root_swap()

    def _root_swap(self):
        """
        Swap rank 0 for whatever root was specified

        If the root has been swapped (ie. is different from default rank 0)
        parent, children and descendants have been calculated correctly for all
        nodes except for where they refer to the root or rank 0.

        We ignore root swap to save calculations in three cases:
        0) When there is no root swap (ie. root is 0)
        1) if it takes place above the parent
        2) if it concerns the equal ranks while we are odd (or vice versa) (excluding rank 0 and its children)

        Otherwise the search  goes through parent, children, descendants in that
        order. If the root is not found to be any of these we can ignore the root
        swap since it happened in an area of the tree that does not concern us.
        """

        # Check if we can ignore root swap totally
        if (self.root == 0) or (self.root < self._parent) or (self.root % 2 != self.rank % 2 and self.rank != 0 and self._parent != 0):
            return None

        self._root_swap_in_children()

    def _root_swap_in_children(self):
        if self._parent == 0: # parent was root so swap
            self._parent = self.root
        elif self._parent == self.root: # parent is to be root so swap
            self._parent = 0

        if self.root in self.child_ranks: # a child is to be root so swap
            for i,cr in enumerate(self.child_ranks):
                if cr == self.root: # found, now swap and stop looking
                    self.child_ranks[i] = 0
                    self._children[0] = self._children.pop(self.root)
                    break
        else: # check for root swap with a descendant
            for cr in self._children:
                cdesc = self._children[cr]['descendants']
                for i,dr in enumerate(cdesc):
                    if dr == self.root: # found, now swap and stop looking
                        cdesc[i] = 0
                        self._children[cr]['descendants'] = cdesc
                        break

class StaticFanoutTree(BinomialTree):

    def __init__(self, size=0, rank=0, root=0, fanout=2):
        self.fanout = fanout
        super(StaticFanoutTree, self).__init__(size=size, rank=rank, root=root)

    def generate_tree(self):
        def get_childs(rank):
            return filter(lambda x: x < self.size, [rank*self.fanout+i for i in range(1, self.fanout+1)])

        r = self.find_substitute_rank()
        self.child_ranks = get_childs(r)

        # Parent
        self._parent = int(math.ceil(float(r)/self.fanout))-1
        if self._parent < 0: self._parent = None

        self._children = {}
        for child in self.child_ranks:

            lookset = [child]
            desc = []
            last_seen = []
            for rank in lookset:
                new_desc = get_childs(rank)
                if last_seen == new_desc: break

                last_seen = new_desc
                desc.extend(new_desc)
                lookset.extend(new_desc)

            self._children[child] = {'descendants' : desc, 'start_iteration' : None}

        self._root_swap()

    def _root_swap(self):
        # Check if we can ignore root swap totally
        if (self.root == 0) or (self.root < self._parent):
            return

        self._root_swap_in_children()

class StaticFanoutTreeRecursive(BinomialTree):
    def __init__(self, communicator, root=0, fanout=2):
        """
        Creating the topology.
        """
        self.fanout = fanout
        super(StaticFanoutTree, self).__init__(communicator, root=root)

    def generate_tree(self):
        ranks = range(self.size)
        ranks.sort()
        ranks.remove(self.root)
        new_ranks = [self.root]
        new_ranks.extend(ranks)

        def node_create(rank, iteration=0):
            return {
              'rank' : rank,
              'children' : [],
              'iteration' :iteration
            }

        root = node_create( new_ranks.pop(0) )
        leafs = [root]

        iteration = 1
        while new_ranks:
            try:
                new_leafs = []
                for leaf in leafs:
                    for _ in range(self.fanout):
                        try:
                            r = new_ranks.pop(0)
                        except IndexError:
                            return root # we are done

                        node = node_create(r , iteration )
                        leaf['children'].append(node)
                        new_leafs.append(node)
                leafs = new_leafs
            except IndexError:
                break

            iteration += 1
        return root
