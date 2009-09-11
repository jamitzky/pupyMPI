"""
Experimenting with a simple broadcast
tree. 

"""

def generate_tree( node_list ):
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

def dot_plot_graph( node ):
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


if __name__ == '__main__':
    tree = generate_tree( range(20) )
    
    dot_plot_graph( tree )
