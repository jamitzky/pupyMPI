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

.. _requirements_for_pupympi:

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
This is perfectly fine as long as there is a Python 2.6 available via the command
``python2.6``

So if you test with::

    python2.6 -V

And you get the output ``Python 2.6.x`` your Python installation should be fine.

pupyMPI assumes that your local filesystem is mirrored on the host you ssh into.
This is the case when using localhost and on most cluster front-ends.

In the case where the python interpreter is somewhere else - eg. you run pupyMPI from
a host where Python 2.6 is at ``/usr/bin/python`` but on the remote nodes Python
2.6 is at ``/usr/local/bin/python2.6`` - you will have to tell pupyMPI the path to
the remote python to use. This is done by adding the parameter ``--remote-python=PATH_TO_PYTHON``
eg.::

    mpirun.py -c 4 --remote-python=/usr/local/bin/python2.6 hello_world.py


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
The minimal pupyMPI program only needs three obligatory lines of code::

    from mpi import MPI # import the pupyMPI library
    mpi = MPI() # initialize pupyMPI
    
    # If you want your program to do something, do it here.
    
    mpi.finalize() # shut down pupyMPI nicely

But programs that do nothing are not much fun, so instead create a file called
``pupympi_test1.py`` and add the following code to it::

    from mpi import MPI
    mpi = MPI()
    
    world = mpi.MPI_COMM_WORLD
    
    rank = world.rank()
    
    message = "Hello world, from rank:%i" % rank
    
    if rank == 0:
        res = world.recv(1)
        print res    
    elif rank == 1:
        world.send(message,0)   
    
    mpi.finalize()

From the command line, run ``mpirun.py -c 2 pupympi_test1.py``.You should receive the message: "Hello world, from rank:1".

If you did not you have one or more problems - see :ref:`troubleshooting_pupympi`.
You may also have to kill stuck Python processes with eg. ``killall python2.6``
 
The test example introduces a few central concepts:
 * the default communicator ``MPI_COMM_WORLD`` which always has all the started processes.
 * ranking
 * sending and receiving
 
You can read more about it all.

.. _troubleshooting_pupympi:

Troubleshooting pupyMPI
-------------------------------------------------------------------------------
If your first pupyMPI program does not work you may have one or more symptoms:

 * **pupyMPI complains about a Python version problem** You probably need to be explicit about your remote Python, as mentioned in :ref:`requirements_for_pupympi` above.
 * **SSH password prompt** Ensure password-less access as mentioned in :ref:`requirements_for_pupympi` above.
 * **No message appears and your script hangs** abort with ``Ctrl+c``, kill any remaining Python processes with ``killall python2.6`` and try againg with the debug ``-d`` parameter added. You will get a metric ton of output.
 

