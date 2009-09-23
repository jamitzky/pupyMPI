=============================================================
Operations
=============================================================

Some API functions like allreduce uses an operator for reducing a list of
elements into a single item, available either to a single root or to all the
processes in a given communicator. Some simple operations include the sum,
min and max function in python, or the ones given later on this page. 

Writing your own operations
----------------------------------------------------------
It's actually very simple. Define a regular python function and give that
as the second argument to (for example) allreduce. If would make an operation
that would nondeterministic give one of the values provided by the members
for the MPI_COMM_WORLD communicator we could do like this::

    def nondet(input_list):
        import random
        return random.choice(input_list)

    from mpi import MPI
    mpi = MPI()

    rank = mpi.MPI_COMM_WORLD.rank()
    random_rank = mpi.MPI_COMM_WORLD.allreduce(rank, nondet)

    mpi.finalize()

.. note::
    This actually shows the power of the operations. Many buildin
    functions in python accepts a list as argument and gives you
    one value back. This means that we could have send a reference
    diretly to random.choice in allreduce with the same result. 

The rest of this page contains some very simple operations for buildin
python types. We end by including some usefull operations for working
with numpy. 

Recommendable internal python functions
----------------------------------------------------------
We have tried to gather a list of internal python functions that might be
interesting to use as operations. The list is by no means complete, and
suggestions are most welcome. 

 * min
 * max
 * random.choice

The :mod:`mpi.operations` Module
----------------------------------------------------------------------
.. automodule:: mpi.operations
    :members: prod, avg


The :mod:`mpi.operations.numpy` Module
-------------------------------------------------------------------------
.. automodule:: mpi.operations.numpy
    :members: mmult
