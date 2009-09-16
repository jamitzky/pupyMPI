The pupympi API documentation
===================================

This is a general documentation of the API part. Please find
information about binaries etc other places. 

The :class:`mpi` class 
-----------------------------
.. module:: mpi
.. autoclass:: MPI
   :members: __init__, initialized, finalize

The :mod:`mpi.request` Module
-----------------------------

.. module:: mpi.request
.. autoclass:: Request
   :members: cancel, test, wait

The :mod:`mpi.collectiverequest` Module
-----------------------------

.. module:: mpi.request
.. autoclass:: CollectiveRequest
   :members: cancel

The :mod:`mpi.communicator` Module
-----------------------------

.. module:: mpi.communicator
.. autoclass:: Communicator
   :members: __init__, rank, size, group, set_name, irecv, isend, attr_get, attr_put, comm_create, comm_free, comm_split, comm_dup, comm_compare, send, barrier, recv, abort, allgather, allgatherv, allreduce, alltoall, alltoallv, bcast, gather, gatherv, reduce, reduce_scatter, scan, scatter, scatterv, start, startall, mname

Contains all the tcp stuff.

