=============================================================
Operations
=============================================================

Some API functions like allreduce uses an operator for reducing a list of
elements into a single item, available either to a single root or to all the
processes in a given communicator. 

It's possible to control the behaviour of these function do very specific 
things, but pupympi with default to a "safe" set of defaults. As a simple
example you can pass the min, max and sum method of regular python to
allreduce (or reduce) like this::

    from mpi import MPI
    mpi = MPI()

    rank = mpi.MPI_COMM_WORLD.rank()
    sum_of_ranks = mpi.MPI_COMM_WORLD.allreduce(rank, sum)

    mpi.finalize()


Writing your own operations
----------------------------------------------------------
It's actually very simple. Define a python function and give that
as the second argument to (for example) allreduce. If would make an operation
that would nondeterministic give one of the values provided by the members
for the MPI_COMM_WORLD communicator we could do like this::

    def product(input_list):
        p = 1
        for e in input_list:
            p *= 1
        return p

    from mpi import MPI
    mpi = MPI()

    rank = mpi.MPI_COMM_WORLD.rank()
    product_of_ranks = mpi.MPI_COMM_WORLD.allreduce(rank+1, product)

    mpi.finalize()

.. note::
    We're adding 1 to the rank just to avoid having the final
    result be 0 every time. 

Control the operations in detail
----------------------------------------------------------
So, why do we need to control the operations? Seems you can do what
you want. But what if you need the ranks of the data? What if you have
enough information about your operation that you know it can be 
calculated by partial operations?

For example. The SUM method can be calculated by partial sums. Ie: 
SUM(SUM(1,2), SUM(0,3)) is the same as SUM(1,2,0,3). But thise is 
not true with the average function. And if you try to make a truly
random choice you'll also want to choose one time from ALL the data
supplied by the processes. If you know your operation can work on
partial sums you can achive a little speed up by setting the "partial_data"
attribute like on our new product::

    def product(input_list):
        p = 1
        for e in input_list:
            p *= 1
        return p

    product.partial_data = True

    from mpi import MPI
    mpi = MPI()

    rank = mpi.MPI_COMM_WORLD.rank()
    product_of_ranks = mpi.MPI_COMM_WORLD.allreduce(rank+1, product)

    mpi.finalize()

The setting defaults to False. 

You can also specify you want a bit more information about the data
you're working on. By setting the "full_meta" attribute you'll get
a list with contributions from each process. Each contribution will
be a dictionary with two keys, "rank" and "value". The rank if the
rank of the contributer and the value is of cause the value. This
setting will normally not be used but are used internally in some
of the other collective requests. This setting defaults to False. 

Recommendable internal python functions
----------------------------------------------------------
We have tried to gather a list of internal python functions that might be
interesting to use as operations. The list is by no means complete, and
suggestions are most welcome. 

 * min
 * max

The :mod:`mpi.operations` Module
----------------------------------------------------------------------
.. automodule:: mpi.operations
    :members: prod, avg


The :mod:`mpi.operations.numpy` Module
-------------------------------------------------------------------------
.. automodule:: mpi.operations.numpy
    :members: mmult
