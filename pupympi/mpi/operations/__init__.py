"""
Operations for collective requests. These will take a
list and do something and return the result. There are
a number of settings you can set on the function itself
that will control the behaviour.

See the documentation for more information.
"""

def MPI_sum(input_list):
    return sum(input_list)
MPI_sum.partial_data = True

def MPI_prod(input_list):
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

MPI_prod.partial_data = True

def MPI_max(input_list):
    """
    Returns the largest element in the list. The input can be any kind of list
    or pseudo list (string, tuple, array etc.).
    
    """
    return max(input_list)
MPI_max.partial_data = True

def MPI_min(input_list):
    """
    Returns the minimum element in the list. 
    """
    return min(input_list)
MPI_min.partial_data = True

def MPI_avg(input_list):
    """
    Return the average of the elements
    """
    return sum(input_list)/len(input_list)
MPI_avg.partial_data = False
