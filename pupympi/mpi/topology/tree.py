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

class BinomialTree(Tree):
    """
    Implement a biniomal tree useful for keeping every node active in
    communication.
    """
    #def __init__(self, communicator, root=0):
    def __init__(self, root=0, rank=0, size=0):
        """
        Creating the topology.
        """
       #self.communicator = communicator
       #self.rank = communicator.comm_group.rank()
       #self.size = communicator.comm_group.size()
        self.root = root
        self.size = size
        self.rank = rank

        self.tree = self.generate_tree()

        self._find_children()
        self._find_parent()

    def _find_parent(self):
        def find(node, candidate):
            if self.rank == node['rank']:
                if candidate:
                    self.parent = candidate['rank']
            else:
                for child in node['children']:
                    find(child, node)

        self.parent = None
        find(self.tree, None)

    def _find_children(self):
        """
        Find all the children of a node.
        If no node is specified all children of calling rank are returned.
        """
        def find(node):
            if self.rank == node['rank']:
                self.children = [x['rank'] for x in node['children']]
            else:
                for child in node['children']:
                    find(child)

        find(self.tree)

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

        def find_all_leafs(node):
            def find_sub(node):
                l = [node]
                childs = node['children']
                if childs:
                    for child in childs:
                        l.extend( find_sub( child ))
                return l
            return find_sub(node)

        root = node_create( new_ranks.pop(0) )

        iteration = 1
        while new_ranks:
            try:
                leafs = find_all_leafs( root )
                for leaf in leafs:
                    leaf['children'].append( node_create( new_ranks.pop(0), iteration ))
            except IndexError:
                break

            iteration += 1
        return root

