#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Experimenting with a simple broadcast
tree. 

"""
import copy

class BroadCastTree(object):
    
    def __init__(self, nodes, rank, root):
        # TODO: initialization could be done more gracefully, no need to remove
        # and extend when a swap could do the trick
        
        # Make sure the root is the first element in the list
        # we use to generate the tree. 
        nodes.sort()
        nodes.remove(root)
        new_nodes = [root]
        new_nodes.extend(nodes)        
        self.nodes = nodes
        self.rank = rank
        self.tree = self.generate_tree(copy.deepcopy(new_nodes))
        self.root = root

        self.up = self.find_up()
        self.down = self.find_down()
        
        #self.descendants = self.find_descendants(rank,self.tree)
        #self.descendants = self.find_descendants(2,self.tree)
        #self.descendants.sort()
        # Descendants of each cild node are stored in a seperate list
        self.descendants = [ self.find_descendants(r, self.tree) for r in self.down ]
        
        #Logger().debug("Tree for rank:%s with root:%s and children:%s and descendants:%s" % (rank,root,self.down,self.descendants))
        
        #if rank in (3,42):
        #    Logger().debug("Tree structure:%s" % self.tree)

        
    def __repr__(self):
        repr = super(BroadCastTree, self).__repr__()
        return repr[0:-1] + "root(%d), rank(%d) up(%s), down(%s)>" % (self.root, self.rank, self.up, self.down)
        

    def find_descendants(self, target=None, subtree=None):
        """
        Find all the descendants of a node.
        If no node is specified all descendants of calling rank are returned.
        """
        if target is None:
            target = self.rank
        
        if subtree is None:
            return []
            
        #Logger().debug("Node:%s" % (subtree))
        
        result = []
        child_nodes = subtree['children']
        if target == subtree['rank']:
            for child in child_nodes:
                result.append(child['rank']) # Add immediate child
                result.extend(self.find_descendants(child['rank'], child)) # Add descendants of child
        else:            
            for child in child_nodes:
                result.extend(self.find_descendants(target, child))
        
        return result
        
        #{
        #'iteration': 0,
        #'children':
        #    [
        #    {'iteration': 1,
        #    'children': [{'iteration': 2, 'children': [], 'rank': 2}, {'iteration': 3, 'children': [], 'rank': 5}],
        #    'rank': 0},
        #    {'iteration': 2,
        #     'children': [],
        #     'rank': 1},
        #    {'iteration': 3,
        #    'children': [],
        #    'rank': 4}
        #    ],
        #'rank': 3
        #}
        
    def find_up(self):
        """
        Iterate from the root and down to find the parent of a node.
        As this is a tree we're limited to one parent but we return a list anyway
        to make the broadcast algorithm more generic.

        How it works:

        from mpi.bc_tree import BroadCastTree

        # We have rank 0
        tree = BroadCastTree(range(10), 0)

        # This should give the empty list
        tree.up

        # We have rank 0
        tree = BroadCastTree(range(10), 1)

        # This should give the root as up
        tree.up
        """
        def find(node, candidate):
            result = []
            if self.rank == node['rank']:
                if candidate:
                    return [candidate]
            else:
                for child in node['children']:
                    result.extend(find(child, node))

            return result
            
        return [x['rank'] for x in find(self.tree, None)]

    def find_down(self, target=None):
        if target is None:
            target = self.rank
        """
        Find all the children of a node.
        If no node is specified all children of calling rank are returned.
        """
        def find(node):
            result = []
            if target == node['rank']:
                return node['children']
            else:
                for child in node['children']:
                    result.extend(find(child))

            return result
            
        return [x['rank'] for x in find(self.tree)]


    def generate_tree(self, node_list ):
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
    
        root = node_create( node_list.pop(0) )
    
        iteration = 1
        while node_list:
            try:
                leafs = find_all_leafs( root )
                for leaf in leafs:
                    leaf['children'].append( node_create( node_list.pop(0), iteration ))
            except IndexError:
                break
    
            iteration += 1
    
        return root
    
    def dot_plot_graph(self, node ):
        def inner_plot(node):
            rank = node['rank']
            for child in node['children']:
                child_rank = child['rank']
                iteration = child['iteration']
    
                if child_rank is not None and rank is not None:
                    print "\t%s -> %s [label=\"Iteration %d\"];" % (rank, child_rank, iteration)
                    inner_plot( child, )
    
        print "digraph G {"
        inner_plot( node );    
        print "}"
