Non blocking collective operations
=================================================================================
pupyMPI extends the MPI specification by supplied the user with non blocking
collective operations. With these it is possible to latency hide communication
as the normal :func:`isend <mpi.communicator.Communicator.isend>` and :func:`irecv
<mpi.communicator.Communicator.irecv>`. 

All the normal collective operations have a non blocking counterpart prefix
with the letter 'i'. For example the non blocking collective version for
:func:`alltoall <mpi.communicator.Communicator.alltoall>` is called
:func:`ialltoall<mpi.communicator.Communicator.ialltoall>`.

Calling a non blocking collective operation combined with a ``wait`` call is
the same as calling the blocking operation::

    import mpi

    mpi = mpi.MPI()
    world = mpi.MPI_COMM_WORLD
    rank = world.rank()

    # blocking version
    gathered = mpi.MPI_COMM_WORLD.allgather(rank)

    # non blocking with wait
    gathered = mpi.MPI_COMM_WORLD.iallgather(rank).wait()

This is actually what happens behind the scenes. Use the non blocking version
if it is possible to hide the communication time while conducting other
calculations. 

The collective request
--------------------------------------------------------------------------
All handles returned from a non blocking collective operation inherit from
a base request described below. 

.. module:: mpi.collective.request
.. autoclass:: BaseCollectiveRequest
   :members: acquire, release, test, wait

