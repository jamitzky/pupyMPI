#!/usr/bin/env python
# encoding: utf-8
"""

"""

import math
import unittest
from operator import mul
from BaseTopology import BaseTopology
from mpi import constants
from mpi.exceptions import MPITopologyException
from mpi.logger import Logger

            
class dummycomm():
    """Mock communicator for unittests only"""            
    def __init__(self, size):
        self.size = size
        import sys
        sys.path.append("../..")
                
    def associate(self, arg):
        pass
        
    def __repr__(self):
        return "dummycomm"
    
    def rank(self):
        return 0
            

class Cartesian(BaseTopology):
    """
    Cartesian topology class for pupyMPI.
    Supports n'th dimensional topologies with flexible size and with periodicity. Rank reordering not supported.
    
    .. note:: 
        if the `periodic` parameter is not supplied or contains less information than `dims` it is automatically extended as False for the remainder of the dimensions.
        It is considered an error to supply a `dims` list of 0 elements or where any element is not a positive integer.
    
    """
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
            raise MPITopologyException("All dimensions must be at least 1 wide")
        if rank_reordering:
            raise MPITopologyException("Rank reordering not supported.")

        if len(periodic) < len(dims):
            periodic.extend([False] * (len(dims) - len(periodic)))
            
        self.dims = dims
        self.periodic = periodic
        self.communicator = communicator
        #Logger("Creating new topology %s and associated with communicator %s." % (self, communicator))
        
    def __repr__(self):
        return "<Cartesian topology, %sD with dims %s>" % (len(self.dims), 'x'.join(map(_writeDimStr, self.dims, self.periodic)))

    def _normalize(self, coords):
        """Normalizes potentially periodic grid coordinates to fit within the grid, if possible, otherwise raise error."""
        normcoords = [c % g if p and c is not g else c for c, g, p in zip(coords, self.dims, self.periodic)]
        for checkcoords, dims in zip(normcoords, self.dims):
            if checkcoords > dims:
                raise MPITopologyException("Grid dimensions overflow")
        return normcoords
        
    # MPI Cartesian functions
    def MPI_Topo_test(self):
        """Return type of topology"""
        return MPI_CARTESIAN
                
    def get(self):
        """
        Get my grid coordinates based on my rank
        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node136.html#Node136
        """
        rank = self.communicator.rank()
        
        return self.coords(rank)
        
    def coords(self, rank):
        """
        The inverse mapping, rank-to-coordinates translation is provided by MPI_CART_COORDS

        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node136.html#Node136
        """
        if self.communicator.size() <= rank:
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
        
    def rank(self, coords):
        """
        Get my 1D rank from grid coordinates
        Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node136.html#Node136
        """
        if len(coords) is not len(self.dims):
            raise MPITopologyException("Dimensions given must match those of this topology.")
            
        coords = self._normalize(coords)
        d = len(coords)
        offset = 0
        
        for k in range(0, d):
            offset += coords[k] * (reduce(mul, self.dims[:k]) if self.dims[:k] else 1)
 
        return offset
        
    def shift(self, direction, displacement, rank_source):
        """Shifts by rank in one coordinate direction. Displacement specifies step width. 
            Original MPI 1.1 specification at http://www.mpi-forum.org/docs/mpi-11-html/node137.html#Node137"""
        if direction >= len(self.dims):
            raise MPITopologyException("Dimensionality exceeded")
            
        rank_target = (rank_source + displacement)
        
        if self.periodic[direction]:
            return rank_target % self.dims[direction]
        elif rank_target < 0 or rank_target >= self.dims[direction]:
            raise MPITopologyException("Shift exceeded grid boundaries")
        
        return rank_target        
    
    def map(self):
        """
        MPI_CART_MAP computes an ''optimal'' placement for the calling process
        on the physical machine. A possible implementation of this function is
        to always return the rank of the calling process, that is, not to
        perform any reordering. 
        
        This implementation does just that, as mapping to physical hardware is
        not supported.
        
        Original MPI 1.1 specification at
        http://www.mpi-forum.org/docs/mpi-11-html/node139.html
        """
        return self.communicator.rank()
        

# convience and "statics"
def _writeDimStr(dim, periodic):
    # used to combine dims and periodic lists for the __repr__ function. There's probably a better way to do this :o
    return "%s%s" % (dim, "P" if periodic else "")

def _isprime(n):
    '''check if integer n is a prime'''
    # range starts with 2 and only needs to go up the squareroot of n
    for x in range(2, int(n**0.5)+1):
        if n % x == 0:
            return False
    return True


def MPI_Cart_Create(communicator):
    """Build a new topology from an existing 1D communicator"""    
    raise NotImplementedException("Cartesian creation targeted for version 1.1")
    return None

    
def MPI_Dims_Create(size, d, constraints = None):
    """
    MPI6.5.2: For cartesian topologies, the function MPI_DIMS_CREATE helps the
    user select a balanced distribution of processes per coordinate direction,
    depending on the number of processes in the group to be balanced and
    optional constraints that can be specified by the user. One use is to
    partition all the processes (the size of MPI_COMM_WORLD's group) into an
    n-dimensional topology. 
    
    This method is not implemented in the public version of pupyMPI because it was not sufficiently stable.
    """      
    
    raise  MPITopologyException("This method is presently not included")

class CartesianTests(unittest.TestCase):
    """Contains stand-alone unit tests for the CartesianTopology class."""
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


    def testCreateDims(self):
        self.assertRaises(MPITopologyException,  MPI_Dims_Create, 6,2,[2,3]) # test fully bound constraint
        ca = MPI_Dims_Create(6,2)
        self.assertEqual(ca, [3,2])
        ca = MPI_Dims_Create(7,2) # test impossible-to-balance value
        self.assertEqual(ca, [7,1])
        ca = MPI_Dims_Create(6,3,[0,3,0])
        self.assertEqual(ca, [2,3,1])
        self.assertRaises(MPITopologyException,  MPI_Dims_Create, 7,3,[0,3,0]) # test unable to reach multiple scenario

        # based on openmpi 3.x        
        ca = MPI_Dims_Create(32,4)
        self.assertEqual(ca, [4,2,2,2])

    # test rank -> [grid coords]
    def testCartGet(self):
        c = dummycomm(10)    
        c.size = 1 # change the size so we can test.
        t = Cartesian(c, [3], [False], None)
        self.assertRaises(MPITopologyException, t.get, 1)
        result = t.get(0)
        self.assertEqual(result, [0])
        
        c.size = 1000 
        result = t.get(0)
        self.assertEqual(result, [0])
        result = t.get(2)
        self.assertEqual(result, [2])

        t = Cartesian(c, [3, 3, 3])
        result = t.get(0)
        self.assertEqual(result, [0, 0, 0])
        result = t.get(13)
        self.assertEqual(result, [1, 1, 1])
        result = t.get(22)
        self.assertEqual(result, [1, 1, 2])

        t = Cartesian(c, [3, 3, 3, 3])
        result = t.get(22)
        self.assertEqual(result, [1, 1, 2, 0])
        
        
    # test [grid coords] -> 1D rank
    def testCartRank(self):
        c = dummycomm(10)    
        t = Cartesian(c, [3], [False], None)
        result = t.rank([0])
        self.assertEqual(result, 0)
        result = t.rank([2])
        self.assertEqual(result, 2)

        t = Cartesian(c, [3, 3], [False], None)
        result = t.rank([0, 0])
        self.assertEqual(result, 0)
        result = t.rank([2, 0])
        self.assertEqual(result, 2)
        result = t.rank([1, 1])
        self.assertEqual(result, 4)
        result = t.rank([2, 2])
        self.assertEqual(result, 8)
        result = t.rank([0, 2])
        self.assertEqual(result, 6)

        t = Cartesian(c, [3, 3, 3], [False,False, False], None)
        result = t.rank([0, 0, 0])
        self.assertEqual(result, 0)
        result = t.rank([2, 0, 1])
        self.assertEqual(result, 11)
        result = t.rank([2, 2, 2])
        self.assertEqual(result, 26)
        result = t.rank([0, 2, 0])
        self.assertEqual(result, 6)

        t = Cartesian(c, [3, 3, 3, 3], [False], None)
        result = t.rank([0, 0, 0, 0])
        self.assertEqual(result, 0)
        result = t.rank([0, 0, 0, 1])
        self.assertEqual(result, 27)

        # need more cases and fix expected result
        
    def testCartShift(self):
        c = dummycomm(10)    
        
        # test non periodic, 1D
        t = Cartesian(c, [50])

        result = t.shift(0, 5, 5)
        self.assertEqual(result, 10)
        result = t.shift(0, 5, -5)
        self.assertEqual(result, 0)
        result = t.shift(0, 0, 45)
        self.assertEqual(result, 45)
        result = t.shift(0, 4, 45)
        self.assertEqual(result, 49)
        result = t.shift(0, -5, 45)
        self.assertEqual(result, 40)
        self.assertRaises(MPITopologyException, t.shift, 0, -10, 5)
        self.assertRaises(MPITopologyException, t.shift, 1, 5, 5)
        
        # test periodic, 1D
        t = Cartesian(c, [50], [True])
        result = t.shift(0, 5, 5)
        self.assertEqual(result, 10)
        result = t.shift(0, 5, -5)
        self.assertEqual(result, 0)
        result = t.shift(0, 0, 45)
        self.assertEqual(result, 45)
        result = t.shift(0, 4, 45)
        self.assertEqual(result, 49)
        result = t.shift(0, 5, 45)
        self.assertEqual(result, 0)
        result = t.shift(0, -5, 45)
        self.assertEqual(result, 40)
        result = t.shift(0, 1024, 45)
        self.assertEqual(result, 19)
        
    def testMap(self):
        c = dummycomm(10)
        t = Cartesian(c, [10, 10, 10])
        result = t.map()
        self.assertEqual(result, 0)
    

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
