import sys

COLLECTIVE_FORCE_BINOMIAL_TREE = True

if COLLECTIVE_FORCE_BINOMIAL_TREE:
    # Disable the flat tree settings.
    FLAT_TREE_MIN = 100
    FLAT_TREE_MAX = 0
    
    # DISABLE HERE AS WELL
    STATIC_FANOUT_MIN = 100
    STATIC_FANOUT_MAX = 0
    
    # Globally enable the binomial tree
    BINOMIAL_TREE_MIN = 0
    BINOMIAL_TREE_MAX = sys.maxint
else:
    FLAT_TREE_MIN = 0
    FLAT_TREE_MAX = 10
    
    # Globally enable the binomial tree
    BINOMIAL_TREE_MIN = 10
    BINOMIAL_TREE_MAX = 50

    STATIC_FANOUT_MIN = 50
    STATIC_FANOUT_MAX = 100
