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
        world.send( np.float32(1.0), 1)
        world.send( np.int_([1,2,4]), 1)
        world.send( np.array([[ 7.,  9.,  7.,  7.,  6.,  3.], 
                [ 5.,  3.,  2.,  8.,  8.,  2.]]), 1)
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
As the following example shows it's also possible to use NumPy data types
in collective operations like bcast::
    
    from mpi import MPI
    import numpy as np
    
    mpi = MPI()
    world = mpi.MPI_COMM_WORLD
    
    rank = world.rank()
    
    if rank == 0:
        world.bcast(root=0, data=np.array([[ 7.,  9.,  7.,  7.,  6.,  3.], 
            [ 5.,  3.,  2.,  8.,  8.,  2.]]))
    else:
        data = world.bcast(0)
        print rank, data
    
    mpi.finalize()

The output of 4 processes running this script is::
    
    3 [[ 7.  9.  7.  7.  6.  3.]
      [ 5.  3.  2.  8.  8.  2.]]
    2 [[ 7.  9.  7.  7.  6.  3.]
      [ 5.  3.  2.  8.  8.  2.]]
    1 [[ 7.  9.  7.  7.  6.  3.]
      [ 5.  3.  2.  8.  8.  2.]]


Using NumPy types in operations for ``reduce``, ``allreduce`` or ``scan``
-------------------------------------------------------------------------------
As long as the chosen operation can work on a list of items the type doesn't 
really matter. The following example shows how to sum a number of vectors where
each process provide a vector::
    
    from mpi import MPI
    import numpy as np
    
    mpi = MPI()
    world = mpi.MPI_COMM_WORLD
    
    data = np.int_([1,2,3])
    
    reduced_data = world.allreduce(data, sum)
    
    print reduced_data
    
    mpi.finalize()

    
The output of 4 processes running this script is::
    
    [ 4  8 12]
    [ 4  8 12]
    [ 4  8 12]
    [ 4  8 12]
