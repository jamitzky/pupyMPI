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
   :members: allgather,allreduce,alltoall,barrier,bcast,comm_compare,comm_create,comm_dup,comm_free,comm_split,gather,get_name,group,irecv,isend,issend,rank,recv,reduce,scan,scatter,send,sendrecv,set_name,size,ssend,testall,testany,testsome,waitall,waitany,waitsome,Wtick,Wtime
