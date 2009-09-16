"""
Experimenting with a simple broadcast
tree. 

"""
import copy

class BroadCastTree:
    
    def __init__(self, nodes, rank):
        nodes.sort()
        self.nodes = nodes
        self.rank = rank
        self.tree = self.generate_tree(copy.deepcopy(nodes))
        
    def up(self):
        idx = self.nodes.index(self.rank) -1
        if idx < 0: 
            return []
        
        return [ self.nodes[ idx ] ]
    
    def down(self):
        try:
            return [ self.nodes[ self.nodes.index(self.rank) +1] ]
        except:
            return []
    
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