#!/usr/bin/env python
# encoding: utf-8
"""
Cartesian.py

Created by Jan Wiberg on 2009-07-21.
"""

import math
import unittest
from operator import mul
from BaseTopology import BaseTopology
from BaseTopology import MPI_CARTESIAN

# Define exception class
class MPITopologyException(Exception): 
    """Custom exception for Topologies"""
    pass

class dummycomm():
    """Haxx communicator for unittests only"""
    def __init__(self, size):
        self.size = size
        import sys
        sys.path.append("../..")
        
        from mpi.logger import setup_log
        self.logger = setup_log( "dummycomm", "proc-%d" % 0, False, 1, False)
        
    def associate(self, arg):
        pass
        
    def __repr__(self):
        return "dummycomm"

class Cartesian(BaseTopology):
    """
    Cartesian topology class for pupyMPI.
    Supports n'th dimensional topologies with flexible size and with periodicity. Rank reordering not supported.
    """
    # TODO Need some sort of check for that communicator size cannot exceed topology (look up order of operations when have inet access: probably at topology creation)
    def __init__(self, communicator, dims, periodic = None, rank_reordering = False ):
        if not periodic:
            periodic = []
            
        # Sanity checks
        if not dims:
            raise MPITopologyException("Zeroth dimensional topology not supported")
        if len(periodic) > len(dims):
            raise MPITopologyException("Cannot have higher dimensionality of periodicity than dimensions")
        if not communicator:
            raise MPITopologyException("No existing communicator given")
        if 0 in dims:
            raise MPITopologyException("All extants must be at least 1 wide")

        # SOLVED  Extend periodic to be same length as dims, use consistent approach to mismatched lists, or disallow althogether
        if len(periodic) < len(dims):
            periodic.extend([False] * (len(dims) - len(periodic)))
            
        self.dims = dims
        self.periodic = periodic
        self.communicator = communicator
        self.logger = communicator.logger
        communicator.associate(self)
        self.logger.info("Creating new topology %s and associated with communicator %s." % (self, communicator))
        
    def __repr__(self):
        return "<Cartesian topology, %sD with dims %s>" % (len(self.dims), 'x'.join(map(_writeDimStr, self.dims, self.periodic)))

    def _normalize(self, coords):
        """Normalizes potentially periodic grid coordinates to fit within the grid, if possible, otherwise raise error."""
        retcords = [c % g if p and c is not g else c for c, g, p in zip(coords, self.dims, self.periodic)]
        # FIXME just do the whole without list comprehensions?
        for checkcoords, dims in zip(retcords, self.dims):
            if checkcoords > dims:
                raise MPITopologyException("Grid dimensions overflow")
        return retcords
        
    # MPI Cartesian functions
    def MPI_Topo_test():
        """Return type of topology"""
        return MPI_CARTESIAN
        
    def MPI_Cart_Create(self, communicator):
        """Build a new topology from an existing 1D communicator"""
        # Might ditch this one
        pass 
        
    def MPI_Cart_get(self, rank):
        """Get my grid coordinates based on my rank"""
        if self.communicator.size <= rank:
            raise MPITopologyException("Rank given exceeds size of communicator")
        
        d = len(self.dims)
        coords = [0] * d
        for k in range(d-1, 0, -1):
            sum = reduce(mul, self.dims[:k])
            coords[k] = rank / sum
            sum *= coords[k]
            rank = max(0, rank - sum)
        coords[0] = rank % self.dims[0]
        
        return coords
        
    def MPI_Cart_rank(self, coords):
        """Get my 1D rank from grid coordinates"""
        if len(coords) is not len(self.dims):
            raise MPITopologyException("Dimensions given must match those of this topology.")
            
        coords = self._normalize(coords)
        d = len(coords)
        offset = 0
        
        for k in range(0, d):
            offset += coords[k] * (reduce(mul, self.dims[:k]) if self.dims[:k] else 1)
 
        return offset
        
    def MPI_Cart_shift(self, direction, displacement, rank_source):
        """Shifts by rank in one coordinate direction. Displacement specifies step width. 
            http://www.mpi-forum.org/docs/mpi-11-html/node137.html#Node137"""
        if direction >= len(self.dims):
            raise MPITopologyException("Dimensionality exceeded")
            
        rank_target = (rank_source + displacement)
        
        if self.periodic[direction]:
            return rank_target % self.dims[direction]
        elif rank_target < 0 or rank_target >= self.dims[direction]:
            raise MPITopologyException("Shift exceeded grid boundaries")
        
        return rank_target        

# convience and "statics"
def _writeDimStr(dim, periodic):
    # used to combine dims and periodic lists for the __repr__ function. There's probably a better way to do this :o
    return "%s%s" % (dim, "P" if periodic else "")

def MPI_Dims_Create(size, desiredDimensions):
    """MPI6.5.2: For cartesian topologies, the function MPI_DIMS_CREATE helps the user select a balanced distribution of processes per coordinate direction, depending on the number of processes in the group to be balanced and optional constraints that can be specified by the user. One use is to partition all the processes (the size of MPI_COMM_WORLD's group) into an n-dimensional topology. """      
    
    # TODO Improve dims_create algorithm
    # FIXME Constrains parameter.
    if desiredDimensions < 1:
        raise MPITopologyException("Dimensions must be higher or equal to 1.")

    base = math.pow (size, 1.0/desiredDimensions)
    dims = [int(base)] * desiredDimensions
    #print("base %s, dims %s" % (base, dims))

    last_empty = 0
    while reduce(mul, dims) < size:
        dims[last_empty] += 1;
        last_empty += 1
        if last_empty >= desiredDimensions:
            last_empty = 0
                
    if reduce(mul, dims) > size:
        raise MPITopologyException("Size (%s) must be a multipla of the resulting grid size (%s)." % (size, dims))
        
    return dims      

class CartesianTests(unittest.TestCase):
    def setUp(self):
        pass
        
    def testCreate(self):
        c = dummycomm(10)
        t = Cartesian(c, [2], [False])
        self.assertEqual(t.dims, [2])
        self.assertEqual(t.periodic, [False])

        t = Cartesian(c, [2, 2], [False])
        self.assertEqual(t.dims, [2, 2])
        self.assertEqual(t.periodic, [False,False])

        t = Cartesian(c, [2, 3, 4, 5, 6, 7], [True])
        self.assertEqual(t.dims, [2, 3, 4, 5, 6, 7])
        self.assertEqual(t.periodic, [True, False, False, False, False, False])
        
    def testCreateError(self):
        c = dummycomm(10)
        
        self.assertRaises(MPITopologyException, Cartesian, None, [2,2])
        self.assertRaises(MPITopologyException, Cartesian, c, [0])
        self.assertRaises(MPITopologyException, Cartesian ,c, [2], [False, False])
        self.assertRaises(MPITopologyException, Cartesian, c, [], [False, False])
            
    def test_normalize(self):
        c = dummycomm(10)

        t = Cartesian(c, [10, 10])
        self.assertEqual(t.periodic, [False, False])

        t = Cartesian(c, [10, 10], [False])
        result = t._normalize([0, 0])
        self.assertEqual(result, [0, 0])
        result = t._normalize([5, 5])
        self.assertEqual(result, [5, 5])
        result = t._normalize([10, 10])
        self.assertEqual(result, [10, 10])
        self.assertRaises(MPITopologyException, t._normalize, [12, 12])

        t = Cartesian(c, [10, 10], [True, True])
        result = t._normalize([0, 0])
        self.assertEqual(result, [0, 0])
        result = t._normalize([5, 5])
        self.assertEqual(result, [5, 5])
        result = t._normalize([10, 10])
        self.assertEqual(result, [10, 10])
        result = t._normalize([12, 12])
        self.assertEqual(result, [2, 2])

        t = Cartesian(c, [10, 10, 10, 10], [True, False, True, False])
        result = t._normalize([12, 10, 12, 9])
        self.assertEqual(result, [2, 10, 2, 9])

        # TODO more tests

    def testCreateDims(self):
        ca = MPI_Dims_Create(6,2)
        self.assertEqual(ca, [3,2])
        # test case fails with current algo
        #ca = MPI_Dims_Create(7,2)
        #self.assertEqual(ca, [7,1])
        self.assertRaises(MPITopologyException,  MPI_Dims_Create, 7,3)

    # test rank -> [grid coords]
    def testCartGet(self):
        c = dummycomm(10)    
        c.size = 1 # fuck around with the size so we can test.
        t = Cartesian(c, [3], [False], None)
        self.assertRaises(MPITopologyException, t.MPI_Cart_get, 1)
        result = t.MPI_Cart_get(0)
        self.assertEqual(result, [0])
        
        c.size = 1000 
        result = t.MPI_Cart_get(0)
        self.assertEqual(result, [0])
        result = t.MPI_Cart_get(2)
        self.assertEqual(result, [2])

        t = Cartesian(c, [3, 3, 3])
        result = t.MPI_Cart_get(0)
        self.assertEqual(result, [0, 0, 0])
        result = t.MPI_Cart_get(13)
        self.assertEqual(result, [1, 1, 1])
        result = t.MPI_Cart_get(22)
        self.assertEqual(result, [1, 1, 2])

        t = Cartesian(c, [3, 3, 3, 3])
        result = t.MPI_Cart_get(22)
        self.assertEqual(result, [1, 1, 2, 0])
        
        
    # test [grid coords] -> 1D rank
    def testCartRank(self):
        c = dummycomm(10)    
        t = Cartesian(c, [3], [False], None)
        result = t.MPI_Cart_rank([0])
        self.assertEqual(result, 0)
        result = t.MPI_Cart_rank([2])
        self.assertEqual(result, 2)

        t = Cartesian(c, [3, 3], [False], None)
        result = t.MPI_Cart_rank([0, 0])
        self.assertEqual(result, 0)
        result = t.MPI_Cart_rank([2, 0])
        self.assertEqual(result, 2)
        result = t.MPI_Cart_rank([1, 1])
        self.assertEqual(result, 4)
        result = t.MPI_Cart_rank([2, 2])
        self.assertEqual(result, 8)
        result = t.MPI_Cart_rank([0, 2])
        self.assertEqual(result, 6)

        t = Cartesian(c, [3, 3, 3], [False,False, False], None)
        result = t.MPI_Cart_rank([0, 0, 0])
        self.assertEqual(result, 0)
        result = t.MPI_Cart_rank([2, 0, 1])
        self.assertEqual(result, 11)
        result = t.MPI_Cart_rank([2, 2, 2])
        self.assertEqual(result, 26)
        result = t.MPI_Cart_rank([0, 2, 0])
        self.assertEqual(result, 6)

        t = Cartesian(c, [3, 3, 3, 3], [False], None)
        result = t.MPI_Cart_rank([0, 0, 0, 0])
        self.assertEqual(result, 0)
        result = t.MPI_Cart_rank([0, 0, 0, 1])
        self.assertEqual(result, 27)

        # need more cases and fix expected result
        
    def testCartShift(self):
        c = dummycomm(10)    
        
        # test non periodic, 1D
        t = Cartesian(c, [50])

        result = t.MPI_Cart_shift(0, 5, 5)
        self.assertEqual(result, 10)
        result = t.MPI_Cart_shift(0, 5, -5)
        self.assertEqual(result, 0)
        result = t.MPI_Cart_shift(0, 0, 45)
        self.assertEqual(result, 45)
        result = t.MPI_Cart_shift(0, 4, 45)
        self.assertEqual(result, 49)
        result = t.MPI_Cart_shift(0, -5, 45)
        self.assertEqual(result, 40)
        self.assertRaises(MPITopologyException, t.MPI_Cart_shift, 0, -10, 5)
        self.assertRaises(MPITopologyException, t.MPI_Cart_shift, 1, 5, 5)
        
        # test periodic, 1D
        t = Cartesian(c, [50], [True])
        result = t.MPI_Cart_shift(0, 5, 5)
        self.assertEqual(result, 10)
        result = t.MPI_Cart_shift(0, 5, -5)
        self.assertEqual(result, 0)
        result = t.MPI_Cart_shift(0, 0, 45)
        self.assertEqual(result, 45)
        result = t.MPI_Cart_shift(0, 4, 45)
        self.assertEqual(result, 49)
        result = t.MPI_Cart_shift(0, 5, 45)
        self.assertEqual(result, 0)
        result = t.MPI_Cart_shift(0, -5, 45)
        self.assertEqual(result, 40)
        result = t.MPI_Cart_shift(0, 1024, 45)
        self.assertEqual(result, 19)
    

    def test__repr__(self):
        c = dummycomm(10)    
        x = Cartesian(c, [2, 3], [False])
        self.assertEqual(str(x), "<Cartesian topology, 2D with dims 2x3>")
        x = Cartesian(c, [2], [True])
        self.assertEqual(str(x), "<Cartesian topology, 1D with dims 2P>")
        x = Cartesian(c, [10, 20, 30], [True, True])
        self.assertEqual(str(x), "<Cartesian topology, 3D with dims 10Px20Px30>")

if __name__ == '__main__':
    unittest.main()