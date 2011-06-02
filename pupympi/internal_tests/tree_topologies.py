"""
Test of different implementations of tree topologies

The only requirements for a tree topology so far is that it
- is created from attributes root, size and rank
- has additional attributes parent and children
- has a function descendants that gives the descendants of a child

"""

from mpi.topology.tree import Tree
from mpi.topology.tree import BinomialTree as BinomialTreeIterative

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
        
        t1 = BinomialTreeIterative(rank=rank, size=size, root=root)
        t2 = BinomialTreeRecursive(rank=rank, size=size, root=root)

        pt1, pt2 = t1.parent(), t2.parent()

        if pt1 != pt2:
            print "t1 parent != t2.parent", pt1, pt2
            
        ct1, ct2 = t1.children(), t2.children()

        if ct1 != ct2:
            print "t1 child ranks != t2.child_ranks", ct1, ct2

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
