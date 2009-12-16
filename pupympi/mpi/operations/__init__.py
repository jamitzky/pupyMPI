"""
Operations for collective requests. These will take a
list and do something and return the result. There are
a number of settings you can set on the function itself
that will control the behaviour.

See the documentation for more information.
"""

def prod(input_list):
    """
    Multiplies all the elements. The elements must be
    integers, float etc. As an example the following code
    uses allreduce to calculate the factorial function of n, 
    where n is the size of the world communicator.::

        from mpi import MPI
        from mpi.operations import prod

        mpi = MPI()

        # We start n processes, and try to calculate n!
        rank = mpi.MPI_COMM_WORLD.rank()
        fact = mpi.MPI_COMM_WORLD.allreduce(rank, prod)

        print "I'm rank %d and I also got the result %d. So cool" % (rank, fact)

        mpi.finalize()
    """
    p = 1

    # The input list is a list of dictionaries. We're only interested in
    # looking through the actual values.

    for e in input_list:
        p *= e
    return p

prod.partial_data = True

def MPI_max(input_list):
    """
    Returns the largest element in the list. The input can be any kind of list
    or pseudo list (string, tuple, array etc.).
    
    """

    return max(input_list)
