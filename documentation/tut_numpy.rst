Working with NumPy in pupyMPI
=================================================================================

The NumPy python package (available from http://numpy.scipy.org/) contains
powerfull data structures and tools for scientific computing. It's possible to
use these strucures within a pupyMPI program as normal data types. 
 
Sending values between processes
-------------------------------------------------------------------------------
As an example the following code sends 3 different NumPy types from rank 0 to
rank 1. Rank 1 will simply print the received data::
    
    from mpi import MPI
    import numpy as np
    
    mpi = MPI()
    world = mpi.MPI_COMM_WORLD
    
    rank = world.rank()
    
    if rank == 0:
        world.send(1, np.float32(1.0))
        world.send(1, np.int_([1,2,4]))
        world.send(1, np.array([[ 7.,  9.,  7.,  7.,  6.,  3.], [ 5.,  3.,  2.,  8.,  8.,  2.]]))
    elif rank == 1:
        for i in range(3):
            r = world.recv(0)
            print type(r), r
    
    mpi.finalize()

Running the above script with at least 2 processes will yield the following output::
    
    <type 'numpy.float32'> 1.0
    <type 'numpy.ndarray'> [1 2 4]
    <type 'numpy.ndarray'> [[ 7.  9.  7.  7.  6.  3.]
    [ 5.  3.  2.  8.  8.  2.]]

Using NumPy in collective operations
-------------------------------------------------------------------------------
skriv mig

Using NumPy types in operations for ``reduce``, ``allreduce`` or ``scan``
-------------------------------------------------------------------------------
skriv mig
