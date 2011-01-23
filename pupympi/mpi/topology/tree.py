"""
Contains different tree topologies. See the :func:`Tree` abstract topology for
the generic API available on all tree topologies. Each implementation can offer
other elements / functions, but the basic API **must** be implemented.
"""

class Tree(object):
    def __init__(self, communicator, root=0):
        """
        Creating the topology.
        """
        self.communicator = communicator
        self.rank = communicator.comm_group.rank()
        self.size = communicator.comm_group.size()
        self.root = root

    def parent(self):
        """
        Returning the rank of the parant, None if the rank is the root of the
        tree.
        """
        raise NotImplementedError()

    def childs(self):
        """
        Return a list of childs ranks. If called on a leaf-node the list
        will be empty.

        Different tree topologies might return list with different length. For
        example a binary tree will return a list of length 0, 1 or 2. A binomial
        tree can send anywhere between 0 l where the size of the tree is fab(l).
        """
        raise NotImplementedError()

    def descendants(self, tree_root_rank=None, base_rank=None, levels=None):
        """
        Find the descendants in the subtree with root ``tree_root_rank`` for
        ``base_rank``. If ``levels`` is supplied the function will only recurse
        the given number of times. If not supplied the recursion will continue
        until all leaf-nodes are found.

        The resursion will - unless otherwise stated below - be a depth first
        recursion.
        """
        raise NotImplementedError()

class FlatTree(Tree):
    """
    Implements a flat free:
        -> Maximum hight is 2 (the root and everything else).
        -> The root has size-1 fanout.
        -> No one other than the root as any childs.
    """
    def childs(self):
        if self.rank == self.root:
            all = range(0, self.size)
            all.remove(self.rank)
            return all
        else:
            return []

    def parent(self):
        if self.rank == self.root:
            return None
        else:
            return self.root

    def descendants(self, tree_root_rank=None, base_rank=None, levels=None):
        # If we are not finding for the root the list is empty.
        if tree_root_rank is None:
            tree_root_rank = self.root

        if base_rank is None:
            base_rank = self.rank

        if tree_root_rank != self.root or base_rank != self.root:
            return []
        else:
            all = range(0, self.size)
            all.remove(self.rank)
            return all
