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

        # Placeholder objects. Each tree must fill the two first with
        # a _find_children and _find_parent method.
        self._children = []
        self._parent = None
        self._descendants = []

        # Generate the tree if there is a bound function with the
        # proper name.
        generator = getattr(self, "generate_tree", None)
        if generator:
            generator()

        self._find_children()
        self._find_parent()

        # Now we have the parent and children (by the actual class). We use
        # a generic method to find the descendants.
        self._find_descendants()

    def _find_descendants(self):
        ## FIXME: This should be implemented and then are are ready to
        # implement the rest of scatter.
        pass

    def parent(self):
        """
        Returning the rank of the parant, None if the rank is the root of the
        tree.
        """
        return self.parent

    def children(self):
        """
        Return a list of children ranks. If called on a leaf-node the list
        will be empty.

        Different tree topologies might return list with different length. For
        example a binary tree will return a list of length 0, 1 or 2. A binomial
        tree can send anywhere between 0 l where the size of the tree is fab(l).
        """
        return self.children

    def descendants(self, tree_root_rank=None, base_rank=None, levels=None):
        """
        Find the descendants in the subtree with root ``tree_root_rank`` for
        ``base_rank``. If ``levels`` is supplied the function will only recurse
        the given number of times. If not supplied the recursion will continue
        until all leaf-nodes are found.

        The resursion will - unless otherwise stated below - be a depth first
        recursion.
        """
        return self.descendants

class FlatTree(Tree):
    """
    Implements a flat free:
        -> Maximum hight is 2 (the root and everything else).
        -> The root has size-1 fanout.
        -> No one other than the root as any children.
    """
    def _find_children(self):
        if self.rank == self.root:
            all = range(0, self.size)
            all.remove(self.rank)
            self._children = all

    def _find_parent(self):
        if self.rank != self.root:
            self._parent = self.root

class BinomialTree(Tree):
    """
    Implement a biniomal tree useful for keeping every node active in
    communication.
    """
    def _find_parent(self):
        def find(node, candidate):
            if self.rank == node['rank']:
                if candidate:
                    self._parent = candidate['rank']
            else:
                for child in node['children']:
                    find(child, node)

        self._parent = None
        find(self.tree, None)

    def _find_children(self):
        """
        Find all the children of a node.
        If no node is specified all children of calling rank are returned.
        """
        def find(node):
            if self.rank == node['rank']:
                self._children = [x['rank'] for x in node['children']]
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
                children = node['children']
                if children:
                    for child in children:
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

class StaticFanoutTree(BinomialTree):

    def __init__(self, communicator, root=0 fanout=2):
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
