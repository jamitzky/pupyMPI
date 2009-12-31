.. _mpirun:

mpirun.py - Starting your processes
===================================

This section contains information about the mpirun.py script you should use to
start pupympi programs. You should include the bin directory of pupympi in your
PATH environment before running the examples in this section.

The script requires one mandatory options -c (the number
of processes to start) and the user script to start::

    > mpirun.py -c 2 the-user-script.py

That's all it takes. Your program will be started and can access the mpi
environment by creating a new instance of the .. class::`MPI` class.

Accepted arguments
-----------------------------
The ``mpirun`` script accepts a lot of argument of different importance. A call
to the script with the ``-h`` flag will show all the available options::
    
    > bin/mpirun.py -h
    Usage: mpirun.py [options] arg

    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -c NP, --np=NP        The number of processes to start.
      --host-file=HOSTFILE  Path to the host file defining all the available
                            machines the processes should be started on. If not
                            given, all processes will be started on localhost
    
      Logging and debugging:
        Use these settings to control the level of output to the program. The
        --debug and --quiet options can't be used at the same time. Trying to
        will result in an error.
    
        -v VERBOSITY, --verbosity=VERBOSITY
                            How much information should be logged and printed to
                            the screen. Should be an integer between 1 and 3,
                            defaults to 1.
        -d, --debug         Give you a lot of input
        -q, --quiet         Give you no input
        -l LOGFILE, --log-file=LOGFILE
                            Which logfile the system should log to. Defaults to
                            mpi(.log)
    
      Advanced options:
        Be careful. You could do strange things here.
    
        --remote-python=REMOTE_PYTHON
                            Path to Python 2.6 on remote hosts. Defaults to
                            `which python2.6`
        --startup-method=method
                            How the processes should be started. Choose between
                            ssh, rsh (not supported) and popen (local only).
                            Defaults to ssh
        --single-communication-thread
                            Use this if you don't want MPI to start two different
                            threads for communication handling. This will limit
                            the number of threads to 3 instead of 4.
        --disable-full-network-startup
                            Do not initialize a socket connection between all
                            pairs of processes. If not a second chance socket pool
                            algorithm will be used. See also --socket-pool-size
        --socket-pool-size=SOCKET_POOL_SIZE
                            Sets the size of the socket pool. Only used it you
                            supply --disable-full-network-startup. Defaults to 20
        --process-io=PROCESS_IO
                            How to forward I/O (stdout, stderr) from remote
                            process. Options are: none, direct, asyncdirect,
                            localfile or remotefile. Defaults to direct
        --hostmap-schedule-method=HOSTMAP_SCHEDULE_METHOD
                            How to distribute the started processes on the
                            available hosts. Options are: rr (round-robin).
                            Defaults to rr
        --enable-profiling  Whether to enable profiling of MPI scripts. Profiling
                            data are stored in
                            ./logs/pupympi.profiling.rank<rank>. Defaults to off.

Passing arguments through to the user script
--------------------------------------------
Normally the internal MPI code will handle all command line arguments and return
an error if one or several arguments can't be recognized. So if your mpi program
accepts arguments like ``-a -b`` the following will **FAIL**::

    # WRONG
    mpirun.py -c -a -b  the-user-script.py 

Instead use the GNU argument-stop sign ``--`` and add the parameters after that.
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
program like ``-c``. We recommend you don't handle argument parsing yourself. Look
into the getopt or optparse module in python.

Distributing the started processes onto several machines
--------------------------------------------------------------
Frederik should write something about how the hostfile works.

