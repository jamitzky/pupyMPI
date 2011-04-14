Working with MPI tags
=================================================================================

 

Filtering messages with tags
-------------------------------------------------------------------------------
It's possible to filter which type of message you
want to receive based on a tag. A very simple example::
    
     from mpi import MPI
     from mpi.constants import MPI_SOURCE_ANY
     mpi = MPI()
     world = mpi.MPI_COMM_WORLD
     rank = world.rank()
     
     
     RECEIVER = 2
     if rank == 0:
         TAG = 1
         world.send("Hello World from 0!", RECEIVER, tag=TAG)
     elif rank == 1:
         TAG = 2
         world.send("Hello World from 1!", RECEIVER, tag=TAG)
     elif rank == 2:
         FIRST_TAG = 1
         SECOND_TAG = 2
         msg1 = world.recv(MPI_SOURCE_ANY, tag=FIRST_TAG)
         msg2 = world.recv(MPI_SOURCE_ANY, tag=SECOND_TAG)
         
         print msg1
         print msg2
     else:
        # disregard other processes
        pass
        
     mpi.finalize()
     
The above example will always print the message from rank 0 before the one
from rank 1. The first :func:`recv <mpi.communicator.Communicator.recv>` 
call will accept messages from any rank, but only with the correct tag. This
is a very useful way to group data and let different subsystems handle it. 

.. _tagrules:

Rules for tags
-------------------------------------------------------------------------------

When you specify tags they should all be positive integers. The internal
MPI system uses negative integers as tags so they are in principle allowed,
but the behaviour of the system if you mix negative tags with anything else than
the normal :func:`recv <mpi.communicator.Communicator.recv>` and :func:`send <mpi.communicator.Communicator.send>`
is undefined. 

There exists a special tag called :func:`MPI_TAG_ANY <mpi.constants.MPI_TAG_ANY>` that will
match any other tag. 

