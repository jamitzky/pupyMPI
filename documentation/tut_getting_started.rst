.. _getting-started: 

***********************************
Getting started with pupyMPI
***********************************

Write me (should assume working knowledge of MPI or not?)

First of, you need a working installation of Python 2.6 (or possibly later) and SSH access to one or more hosts. This may just be *localhost*, as long as you're just testing. SSH must have been set up to allow direct access (see http://linuxproblem.org/art_9.html). 

First ensure that pupyMPI is in your Python path. FIXME FIXME FIXME.

.. note::
    Some installations do not have Python 2.6 as the global default Python installation. You can verify this by doing this after the command line::
        ssh localhost python -V
        
    It should firmly state that it is indeed a Python 2.6 or better. In case it is not, find the path to Python 2.6 and remember it (``which python2.6`` should do the trick). You will need to tell pupyMPI where to find Python2.6, and you'll do this by adding the parameter --remote-python=path_to_python2.6 to mpirun.py.  FIXME: its possible to pipe which output into ssh, but popen fucks it up!!!!



---------------------
Differing conventions
---------------------
You are probably already familiar with MPI for C. However, pupyMPI differs from a C/FORTRAN implementation in several different regards. The most important are:

* No data types - anything goes (there is a size limit to individual messages, however)
* Buffering / memory storage / garbage collection
    
    * No bsend etc
    
* Object model
* 1 or 0 replaced with True and False
* (possibly) NULL handles replaced with None
* Local function changes: check the documentation and make no assumptions!
 
--------------------------
Your first pupyMPI program
--------------------------

#. Create a file called pupympi_test1.py and add the following code to it.
 Rank 0 sends "Hello world!" to rank 1. Rank 1 receives the message
 and prints it::
     
     from mpi import MPI
     mpi = MPI()

     if mpi.MPI_COMM_WORLD.rank() == 0:
         mpi.MPI_COMM_WORLD.send(1, "Hello World!")
     else:
         message = mpi.MPI_COMM_WORLD.recv(0)
         print message

#. From the command line, run ``mpirun -c 2 pupympi_test1.py``.


#. You should receive the message: "Hello World!".

That was easy, wasn't it? Some things could have gone wrong though:

If pupyMPI complains about a Python version problem
    you probably need to be explicit about your Python, as mentioned above. You'll also probably have to kill stuck Python processes by ``killall python`` (or ``killall Python``)
    
"Command not found"
    Make sure pupyMPI is in your PYTHONPATH. It should be installed as an egg or module. It is also possible to start pupyMPI by cd'ing to the root directory and try this instead ``PYTHONPATH=. bin/mpirun -c 2 /path/to/pupympi_test1.py``
    
SSH password prompt
    Ensure password-less access
    
No message appears and your script hangs
    ctrl-c, kill all Python processes and use the -d parameter in addition to the others. You will get a metric ton of output. If you can't figure the error out yourself, feel free to contact us. FIXME riiiiiiiiiiiiight.

Anything else?
    Try asking us.

