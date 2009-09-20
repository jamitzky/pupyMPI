.. _mpirun:

mpirun.py - Starting your processes
===================================

This section contains information about the mpirun.py script you should use to
start pupympi programs. You should include the bin directory of pupympi in your
PATH environment before running the examples in this section.

The script requires one mandatory options -c (the number
of processes to start) and the user script to start::

    > mpirun.py -c=2 the-user-script.py

That's all it takes. Your program will be started and can access the mpi
environment by creating a new instance of the .. class:: MPI class.

Accepted arguments
-----------------------------
write something about the argument handling here

Passing arguments through to the user script
--------------------------------------------
Normally the internal mpi code will handle all command line arguments and return
an error if one or several arguments can't be recognized. So if your mpi program
accepts arguments like "-a -b" the following will **FAIL**::

    # WRONG
    mpirun.py -c -a -b  the-user-script.py 

Instead use the GNU argument-stop sign "--" and add the paramters after that.
For example::

    # RIGHT
    mpirun.py -c the-user-script.py -- -a -b  

If "the-user-script.py" was defined by the following code::

    #!/usr/bin/env python2.6
    import mpi, sys

    mpi = mpi.MPI()
    print sys.argv
    mpi.finalize()

The output of running the above command would be::

    > mpirun.py -c 2 the-user-script.py -- -a -b
    ['/full/path/to/the-user-script.py', ['-a', '-b']]
    ['/full/path/to/the-user-script.py', ['-a', '-b']]

You can even pass arguments that are elsewhere reserved by the mpirun.py 
program like "-c". We recommend you don't handle argument parsin yourself. Look
into the [getopt]_ or [optparse]_ module in python.

.. [getopt] getopt module documentation available from
.. [optparse] optparse moduel documentation available from
