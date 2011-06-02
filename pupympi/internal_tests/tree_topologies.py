"""
Test of different implementations of tree topologies

The only requirements for a tree topology so far is that it
- is created from attributes root, size and rank
- has additional attributes parent and children
- has a function descendants that gives the descendants of a child

"""


class Tree(object):
    def __init__(self, root=0, size=1, rank=0):
        """
        Creating the topology.
        """
        # checking validity
        if (rank >= size) or size<1:
            raise Exception("Bad tree topology!")

        if (root >= size):
            raise Exception("Bad tree topology by root!")

        self.size = size
        self.root = root
        self.rank = rank

        # These will be set by the tree generator function
        self.parent = None
        self.child_ranks = []
        self.children = {}

        # Generate the tree if there is a bound function with the proper name
        generator = getattr(self, "generate_tree", None)
        if generator:
            generator()


class BinomialTreeIterative(Tree):
    def generate_tree(self):
        """
        If
        a) Every node can send one copy of the message to another rank in one iteration
        b) No node but the root can send before receiving from another node (a parent)

        The maximum depth d of the binomial tree is ???

        Then a message is propagated through a tree of 2^i nodes in i iterations

        A node with rank r receives the message from its parent in iteration i
        where 2^(i-1) <= r < 2^i

        In iteration i a node with rank r sends to the receiver with rank n
        where n = 2^i + r

        A node with rank r in a tree of size s has the parent p
        where p = r - 2**(i_start-1)

        children = { rank: { 'descendants': [d1,d2,...], 'start_iteration': i,  }, ... }
        """
        # Is this node involved in root swap?
        if self.rank == 0 and self.root != 0:
            r = self.root  # Fake being a lower rank
        elif self.rank == self.root:
            r = 0 # Fake being root
        else:
            r = self.rank # Be yourself

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
        self.parent = int(r - 2**(i_start-1))

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
                desc = [ dr for dr in desc[1:] if r < s ]

                self.children[r_child] = {'descendants' : desc, 'start_iteration' : i}
            else:
                break
            i += 1

        # Now swap if needed
        self._root_swap()

        #print "for a tree of size:%i rank %i receives from parent:%i in iteration %i final_i:%i child_ranks:%s" % (self.size, self.rank, self.parent, i_start, i_final, self.child_ranks)
        #print "for a tree of size:%i rank %i receives from parent:%i in iteration %i final_i:%i child_ranks:%s \nchildren:%s" % (self.size, r, p, i_start, i_final, child_ranks, children )

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
        if (self.root == 0) or (self.root < self.parent) or (self.root % 2 != self.rank % 2 and self.rank != 0 and self.parent != 0):
            return None
        else:
            if self.parent == 0: # parent was root so swap
                self.parent = self.root
            elif self.parent == self.root: # parent is to be root so swap
                self.parent = 0

            if self.root in self.child_ranks: # a child is to be root so swap
                for i,cr in enumerate(self.child_ranks):
                    if cr == self.root: # found, now swap and stop looking
                        self.child_ranks[i] = 0
                        self.children[0] = self.children.pop(self.root)
                        break
            else: # check for root swap with a descendant
                for cr in self.children:
                    cdesc = self.children[cr]['descendants']
                    for i,dr in enumerate(cdesc):
                        if dr == self.root: # found, now swap and stop looking
                            cdesc[i] = 0
                            self.children[cr]['descendants'] = cdesc
                            break

    def parent(self):
        """
        Returning the rank of the parent, None if the rank is the root of the
        tree.
        """
        if self.rank == self.root:
            return None
        else:
            return self.parent

    def children(self):
        """
        Acessor for child ranks. Might be superflous later on.
        """
        return self.child_ranks

    def descendants(self, child_rank):
        """
        return the descendants of a given rank
        """
        return self.children[child_rank]['descendants']

class BinomialTreeRecursive(Tree):
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

    def _find_descendants(self):
        """
        This creates a dict, which values are lists. Each child for the
        rank of this process has a list with all their descendants.
        """
        if not self.tree:
            raise Exception("Topology cant find descendants without a generated tree.")

        # The idea is to iterate until we find onw of our children. When this is done
        # the iteration process will register every seen node from that point as a
        # descendant.
        def rec(node, child=None):
            def ensure(rank):
                if rank not in self._descendants:
                    self._descendants[rank] = []

            def register(rank, desc_rank):
                ensure(rank)
                self._descendants[rank].append(desc_rank)

            # We have already found a child to register for, so we just
            # return the data and resurse a bit more
            if child is not None:
                register(child, node['rank'])
                # Iterate
                for node_child in node['children']:
                    rec(node_child, child=child)
            # We have not found which child to look for. So if this node is
            # actually the child of our rank every descendants from there should
            # be registered.
            else:
                if node['rank'] in self.children():
                    # ensure structure
                    ensure(node['rank'])
                    child = node['rank']

                for node_child in node['children']:
                    rec(node_child, child=child)
        rec(self.tree)

def compare():
    def inner_compare(size=1, rank=0, root=0):
        t1 = BinomialTreeIterative(size=size, rank=rank, root=root)
        t2 = BinomialTreeRecursive(size=size, rank=rank, root=root)

        if t1.parent != t2.parent:
            print "t1 parent != t2.parent", t1.parent, t2.parent

        if t1.child_ranks != t2.child_ranks:
            print "t1 child ranks != t2.child_ranks", t1.child_ranks, t2.child_ranks

    inner_compare(size=10, rank=0, root=0)



if __name__ == "__main__":
    import sys

    # Check first if we should compare the two classes.
    if "compare" in sys.argv:
        compare()
        sys.exit(0)

    if len(sys.argv) != 3:
        print "There should be two and only two arguments for the benchmarker. Use 'old' to benchmark the old structure and 'new' to benchmark the new one as the first parameter. The second is a filepath indicating where to store the benchmark files"

    if sys.argv[-2] == "new":
        print "Benchmarking new tree structure"
        identifier = 'BinomialTreeIterative'
        tr = BinomialTreeIterative

    elif sys.argv[-2] == "old":
        print "Benchmarking old tree structure"
        tr = BinomialTreeRecursive
        identifier = 'BinomialTreeRecursive'
    else:
        print "Can't recognize the arguments. Use either 'old' or 'new'"

    from mpi.benchmark import Benchmark
    b = Benchmark(None)

    for size in range(0, 50001, 500)[1:]:
        print "Starting with size", size
        tester, _ = b.get_tester(identifier, procs=1, datasize=size)

        for root in range(0, 1000):
            root = root % size
            with tester:
                tr(root=root, size=size, rank=0)

    b.flush(sys.argv[-1])
