.. _getting-started: 

Getting started with pupyMPI
=================================================================================

pupyMPI is a pure python MPI implementation of MPI 1.3 with some added features.
This document is not a manual of general MPI concepts but rather a reference
manual for pupyMPI.

In the following we assume that you are familiar with the basic
concepts of MPI. If you are not, there are lots of excellent introductions out
there: 
http://www.google.com/search?q=introduction+to+mpi

We also assume that you have not previously used pupyMPI so we will start from
scratch. If you know you have the required stuff installed and your pupyMPI
installation is working you can skip to the section :ref:`your_first_pupympi_program`.

With that out of our way - let's get this party started.

Requirements for pupyMPI
-------------------------------------------------------------------------------
pupyMPI requires

* Python (version 2.6 or 2.7)
* SSH
* Linux or Mac OSX

pupyMPI uses SSH to start processes on remote hosts so you will need to have
SSH installed. For your own sanity you should have passwordless access or you will
be very busy typing passwords for each MPI process you start up.

When you are just developing or testing you can of course run everything on
*localhost*. But eventually you will want network access to one or more hosts
where you can spawn and run your MPI processes. The way you tell pupyMPI where
to spawn remote processes is via the ``hostfile``. You can read more about it here
:ref:`using_the_hostfile` but just ignore it for now since
pupyMPI defaults to localhost if it does not find a proper hostfile.

You can check that SSH is installed and works (locally) with::

    ssh localhost


This should give you a shell on your own machine which you can of course just
exit from again. Note that if you are asked for a password in the terminal you
have yet to setup proper passwordless access (see http://linuxproblem.org/art_9.html).

When you want to run pupyMPI on other hosts (remote machines) you should ensure
that you have the same access, ie. try::
    
    ssh SOME_REMOTE_HOST


Some installations do not have Python 2.6 as the global default Python installation. 
You can verify that you have the right version with::
    
    python -V

In case you see something else than 2.6.x or 2.7.x, you must find the path to Python 2.6
and remember it, eg.::
    
    which python2.6
     

You will now need to tell pupyMPI where to find Python 2.6 when you run stuff,
and you'll do this by adding the parameter ``--remote-python=path_to_python2.6``
after ``mpirun.py``



Differing conventions
-------------------------------------------------------------------------------
You might already be familiar with MPI for C or FORTRAN. However, pupyMPI 
differs from a C/FORTRAN implementation in several different regards. 
The most important are:

* No data types - anything goes (there is a size limit to individual messages, however)
* Buffering / memory storage / garbage collection. No bsend etc.
* Object model. You call ``request.wait()`` instead for something like ``MPI_Wait(request)``. 
* 1 or 0 replaced with True and False
* NULL handles replaced with None
* Local function changes: check the documentation and make no assumptions!

.. _your_first_pupympi_program:

Your first pupyMPI program
-------------------------------------------------------------------------------
Create a file called pupympi_test1.py and add the following code to it::
     
     from mpi import MPI
     mpi = MPI()

     if mpi.MPI_COMM_WORLD.rank() == 0:
         mpi.MPI_COMM_WORLD.send("Hello World!", 1)
     else:
         message = mpi.MPI_COMM_WORLD.recv(0)
         print message
     mpi.finalize()
     
From the command line, run ``mpirun.py -c 2 pupympi_test1.py``.You should receive the message: "Hello World!"
If you did not you might have run into one of these problems:

 * **pupyMPI complains about a Python version problem** You probably need to be explicit about your Python, as mentioned above. You'll also probably have to kill stuck Python processes by ``killall python`` (or ``killall Python``)
 * **SSH password prompt** Ensure password-less access
 * **No message appears and your script hangs** ctrl-c, kill all Python processes and use the ``-d`` parameter in addition to the others. You will get a metric ton of output. 
 
The above test example introduces the ``MPI_COMM_WORLD`` communicator holding all the
started processes.

.. note:: If you run the above script with more than 2 participants, the script will hang. This is due to the participants with higher rank than 1. These will try to receive a message from rank 0, but such a message is never sent.

Filtering messages with tags
-------------------------------------------------------------------------------
Unlike the previous example it's possible to filter which type of message you
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
is a very usefull way to group data and let different subsystems handle it. 

.. _tagrules:

Rules for tags
-------------------------------------------------------------------------------

When you specify tags they should all be possitive integers. The internal
MPI system use negative integers as tags so they are in principle allowed,
but the behaviour of the system if you mix negative tags with anythin else than
the normal :func:`recv <mpi.communicator.Communicator.recv>` and :func:`send <mpi.communicator.Communicator.send>`
is undefined. 

There exist a special tag called :func:`MPI_TAG_ANY <mpi.constants.MPI_TAG_ANY>` that will
match any other tag. 

