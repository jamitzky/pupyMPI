"""
Test of different implementations of tree topologies

The only requirements for a tree topology so far is that it
- is created from attributes root, size and rank
- has additional attributes parent and children
- has a function descendants that gives the descendants of a child

"""

from mpi.topology.tree import Tree
from mpi.topology.tree import BinomialTree as BinomialTreeIterative
import copy

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
                self.child_ranks = [x['rank'] for x in node['children']]
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
        leafs = []

        def node_create(rank, iteration=0):
            node = {
              'rank' : rank,
              'children' : [],
              'iteration' :iteration
            }
            leafs.append(node)
            return node

        root = node_create( new_ranks.pop(0) )

        iteration = 1
        while new_ranks:
            try:
                itleafs = copy.copy(leafs)
                for leaf in itleafs:
                    leaf['children'].append( node_create( new_ranks.pop(0), iteration ))
            except IndexError:
                break

            iteration += 1

        self.tree = root

        # Call internal functions for finding / setting children etc
        self._find_parent()
        self._find_children()
        self._find_descendants()

    def _find_descendants(self):
        """
        This creates a dict, which values are lists. Each child for the
        rank of this process has a list with all their descendants.
        """
        if not self.tree:
            raise Exception("Topology cant find descendants without a generated tree.")

        # We create the data structure that will hold all the descendants.
        self._children = {}
        for r in range(self.size):
            self._children[r] = {'descendants' : []}

        # Go though the tree with a list of ranks found above. This means that
        # each of those ranks will have the current rank in its descendants.
        def recurse(node, ancestors):
           # print "Called with ancestors", ancestors

            for rank in ancestors:
                self._children[rank]['descendants'].append(node['rank'])

            # Create a new list with this rank on it
            new_ancestors = copy.copy(ancestors)
            new_ancestors.append(node['rank'])

            for child in node['children']:
                recurse(child, new_ancestors)

        recurse(self.tree, [])

def compare():
    def inner_compare(size=1, rank=0, root=0):
        t1 = BinomialTreeIterative(rank=rank, size=size, root=root)
        t2 = BinomialTreeRecursive(rank=rank, size=size, root=root)

        pt1, pt2 = t1.parent(), t2.parent()
        error = False

        debug = "\n===================== Compare report ====================="

        pmatch = pt1 == pt2
        debug += "\nParent match:" + str(pmatch)
        if not pmatch:
            error = True
            debug += "\n\tRecursive: " + str(pt2)
            debug += "\n\tIterative: " + str(pt1)

        ct1, ct2 = t1.children(), t2.children()

        # We need to sort as it otherwise might fail in compare
        ct1.sort()
        ct2.sort()

        cmatch = ct1 == ct2
        debug += "\nChildren match: " + str(cmatch)
        if not pmatch:
            error = True
            debug += "\n\tRecursive: " + str(ct2)
            debug += "\n\tIterative: " + str(ct1)

        for r in ct1:
            d1 = t1.descendants(r)
            d2 = t2.descendants(r)

            d1.sort()
            d2.sort()

            dmatch = d1 == d2
            debug += "\nChildren match for child rank " + str(r) + " " + str(dmatch)
            if not dmatch:
                error = True
                debug += "\n\tRecursive: " + str(d2)
                debug += "\n\tIterative: " + str(d1)
        debug += "\n=========================================================="
        return error, debug

    C = 100000
    import random
    print "Sampling starting. Running %d samples" % C
    errors = 0

    for i in range(C):
        size = random.randint(1, 10000)
        root = random.randint(0, size-1)
        rank = random.randint(0, size-1)
        print "\tSample %d: size(%d), rank(%d), root(%d)" % (i, size, rank, root)
        error, debug = inner_compare(size=10, rank=0, root=0)
        if error:
            errors =+ 1

    print "A total of %d errors" % errors

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

    for size in range(0, 50001, 1000)[1:]:
        print "Starting with size", size
        tester, _ = b.get_tester(identifier, procs=1, datasize=size)

        for root in range(0, 100):
            root = root % size
            with tester:
                tr(root=root, size=size, rank=0)

    b.flush(sys.argv[-1])
