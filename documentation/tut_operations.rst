.. _operations-api-label:

=============================================================
Custom reducing operations
=============================================================

The :func:`allreduce <mpi.communicator.Communicator.allreduce>`, 
:func:`reduce <mpi.communicator.Communicator.reduce>` and
:func:`scan <mpi.communicator.Communicator.scan>` functions allows
you to specify which operation the data should be reducing with. 

It's possible to control the behaviour of these function do very specific 
things, but pupympi with default to a "safe" set of defaults. As a simple
example you can pass the ``min``, ``max`` and ``sum`` method of regular python to
:func:`allreduce <mpi.communicator.Communicator.allreduce>` like this::

    from mpi import MPI
    mpi = MPI()

    rank = mpi.MPI_COMM_WORLD.rank()
    sum_of_ranks = mpi.MPI_COMM_WORLD.allreduce(rank, sum)

    mpi.finalize()

The operations are thus just regular python function taking a list 
as the only parameter. This makes it possible to write your own
operations very simple. For example, the available
:func:`MPI_avg <mpi.operations.MPI_avg>` 
was implemented simply as::
    
    def MPI_avg(input_list):
        return sum(input_list)/len(input_list)

and :func:`MPI_min <mpi.operations.MPI_min>` is implemented like::

    def MPI_min(input_list):
        return min(input_list)
    MPI_min.partial_data = True

Setting the ``partial_data`` on the operation is explaining 
in the next section. 

Control the operations in detail
----------------------------------------------------------
Setting the ``partial_data`` attribute on an operation  
tells pupyMPI that is's safe of apply the operation on
an incomplete dataset. That will allow the system to
reduce data on the fly and limit the data needed to send
between the processes. 

For example. The SUM method can be calculated by partial sums. Ie: 
SUM(SUM(1,2), SUM(0,3)) is the same as SUM(1,2,0,3). But thise is 
not true with the average function. 

Another example would be how to make a truly
random choice. You'll want to choose **one** time from **ALL** the data
supplied by the processes, but make choices from minor selections and 
then choosing from these again. 

The default setting of ``partial_data`` is False


