def avg(input_list):
    """
    Calculate the average of the numbers given by the processes. This is 
    an example of an operation that can't calculate intermediate results,
    but must wait until all the numbers have been gathered. 
    """
    # FIXME: See doc note of why this is wrong
    return sum(input_list)/len(input_list)

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
    for e in input_list:
        p *= e
    return p

