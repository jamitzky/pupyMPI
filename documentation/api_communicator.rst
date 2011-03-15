.. _api-communicator-label:

Communicator object 
-------------------------------------------------------------------------------

This class represents an MPI communicator. The communicator holds information
about a 'group' of processes and allows for inter communication between these. 

It's not possible from within a communicator to talk with processes outside. Remember
you have the :func:`MPI_COMM_WORLD <mpi.MPI.MPI_COMM_WORLD>` communicator holding **all** the started proceses. 

Communicators should not be created directly, but created through the :func:`comm_create <mpi.communicator.Communicator.comm_create>`,
:func:`comm_split <mpi.communicator.Communicator.comm_split>` or :func:`comm_dup <mpi.communicator.Communicator.comm_dup>` methods. 

.. module:: mpi.communicator
.. autoclass:: Communicator
   :members: allgather, iallgather, allreduce, iallreduce, alltoall, ialltoall, barrier, ibarrier, bcast, ibcast, comm_compare, comm_create, comm_dup, comm_free, comm_split, gather, igather, get_name, group, recv, irecv, send, isend, ssend, issend, rank, reduce, ireduce, scan, iscan, scatter, iscatter, sendrecv, set_name, size, testall, testany, testsome, waitall, waitany, waitsome, Wtick, Wtime
