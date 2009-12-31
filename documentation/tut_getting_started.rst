.. _getting-started: 

***********************************
Getting started with pupyMPI
***********************************

pupyMPI is a pure python MPI implementation for educational use. This document
does not in any way try to explain general MPI concepts, but it merely a reference
manual to pupyMPI. 

Required software and versions
-------------------------------------------------------------------------------
pupyMPI requires python version 2.6 or later, due to some process management
tool in the subprocess module. It's not tested with python 3. 
    
You should ensure pupyMPI is in your ``PYTHONPATH``, which can be done like::
    
    export PYTHONPATH=/path/to/pupympi/:$PYTHONPATH

Some installations do not have Python 2.6 as the global default Python installation. 
You can verify this by doing this after the command line::
    
    ssh localhost python -V

In case it is not, find the path to Python 2.6 and remember it::
    
    which python2.6
     
You will need to tell pupyMPI where to find Python2.6, and you'll do this by adding the 
parameter ``--remote-python=path_to_python2.6`` to ``mpirun.py``

You also need SSH access to one or more hosts.  This may just be *localhost*, as long as you're just testing. 
SSH must have been set up to allow direct access (see http://linuxproblem.org/art_9.html). 


Differing conventions
-------------------------------------------------------------------------------
You might already be familiar with MPI for C or FORTRAN. However, pupyMPI 
differs from a C/FORTRAN implementation in several different regards. 
The most important are:

* No data types - anything goes (there is a size limit to individual messages, however)
* Buffering / memory storage / garbage collection. No bsend etc
* Object model. You call ``request.wait()`` instead for something like ``MPI_Wait(request)``. 
* 1 or 0 replaced with True and False
* NULL handles replaced with None
* Local function changes: check the documentation and make no assumptions!
 
Your first pupyMPI program
-------------------------------------------------------------------------------
Create a file called pupympi_test1.py and add the following code to it::
     
     from mpi import MPI
     mpi = MPI()

     if mpi.MPI_COMM_WORLD.rank() == 0:
         mpi.MPI_COMM_WORLD.send(1, "Hello World!")
     else:
         message = mpi.MPI_COMM_WORLD.recv(0)
         print message

From the command line, run ``mpirun -c 2 pupympi_test1.py``.You should receive the message: "Hello World!"
If you did not you might have run into one of these problems:

 * **pupyMPI complains about a Python version problem** You probably need to be explicit about your Python, as mentioned above. You'll also probably have to kill stuck Python processes by ``killall python`` (or ``killall Python``)
 * **Command not found** Make sure pupyMPI is in your ``PYTHONPATH``. It should be installed as an egg or module. It is also possible to start pupyMPI by cd'ing to the root directory and try this instead ``PYTHONPATH=. bin/mpirun -c 2 /path/to/pupympi_test1.py``
 * **SSH password prompt** Ensure password-less access
 * **No message appears and your script hangs** ctrl-c, kill all Python processes and use the ``-d`` parameter in addition to the others. You will get a metric ton of output. 
