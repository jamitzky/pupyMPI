Utilities
======================================================================
pupyMPI ships with a number of utility scripts making it possible to
communicate with a running instance. Each script may have some 
individuelle arguments and parameters, but unless otherwise specified
in the call documentation the usage of a program is:: 

    > some-script.py -r <ranks> <handle-file>

The ``<ranks>`` parameters is optional, but if present it filters which
ranks of the running instance should receive the command.

The ``<handle-file>`` contains information needed to communicate with the
instance. The file is written when the instance is started. See the
documentation for :doc:`mpirun` for how to locate the file. 

.. note:: Most of the functionality here need to be executed in
    the main execution code. We need to wait until the user
    program calls into the MPI framework before running the 
    wanted commands. By extension - this means that if a process
    is stuck in a user-code infinite loop, the system command
    will never be executed. If you get timeouts, this might be
    the reason. 


pupy_abort.py
-----------------------------
As the name suggest this script will try to abort the instance. The script
will print if the abort message was sent correct. It can not check if the
rank actually aborted. An example run::

    > PYTHONPATH=../..:.. ./pupy_abort.py /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupywH_68X
    abort message successful sent to 0
    abort message successful sent to 1
    abort message successful sent to 2
    abort message successful sent to 3

.. warning:: You can not use this ulitity to kill your MPI program if it is
    stuck in an infinite loop (in user code). It is not possible to call
    ``sys.exit()`` in a thread as it will act as ``Thread.exit``. Therefore
    the abort code will first be issued when the user calls into MPI. 

pupy_ping.py
-----------------------------
A simple way to check if your processes are active and running. The script
has a 30 second timeout on receiving a pong from each of the ranks. If by
that time the processes sends the pong you can expect output like::

    > PYTHONPATH=../..:.. python pupy_ping.py /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupyVGFcIb 
    Pong received for rank 0: True
    Pong received for rank 1: True
    Pong received for rank 2: True
    Pong received for rank 3: True

If by the other hand the user code never calls any MPI functions the script
will report a timeout. The timeout does not mean that the code will **never**
reach a MPI function. It just means that it did not happen within the 30
seconds::

    > PYTHONPATH=../..:.. python pupy_ping.py /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupyjtK5NZ
    0: Connection timeout (30 seconds)
    1: Connection timeout (30 seconds)
    2: Connection timeout (30 seconds)
    3: Connection timeout (30 seconds)

.. _readregister:

pupy_readregister.py
-----------------------------
The main :func:`MPI` object has a dict called :func:`MPI.user_register` where
it is possible for the user to input values. This utility script extract 
these values and prints them on ``STDOUT``. 

**Limiting the outout**: It is posible to limit the number of processes asked
like the above scripts, but it is also possible to furhter limit the output
by using the ``-i`` and ``--index=`` flags to indicate which keys from the
dict should be extracted.

The following python code shows a small MPI program *faking* a SOR. After each
interation the user register is updated::

    from mpi import MPI
    import time, random

    def solver(iterations):
        mpi = MPI()

        world = mpi.MPI_COMM_WORLD
        rank = world.rank()
        delta = 1

        for i in range(iterations):
            # Calc takes times
            time.sleep(0.1)

            # Fake a delta.
            delta = min(delta, random.random())

            # Take the sum of the delta
            world_delta = world.allreduce(delta, sum)

            # Update the user register
            mpi.user_register = {
                'delta' : delta,
                'world_delta' : world_delta,
                'iterations' : i,
            }

    if __name__ == "__main__":
        solver(10000)

**Result**
First the sor is started::

    > python ../../bin/mpirun.py -c 3 sor_like_solver.py 
    2010-12-18 13:30:45 mpirun      : WARNING  Insufficient hosts - overmapping processes.
    Process handle written (use pupysh to interact with the running system) to: /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupyShSSrS

At any point we can inpect the register as the below output shows::

    > python pupy_readregisters.py /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupyShSSrS
    ---------------- Registers for rank 0 -------------------
    world_delta: 0.115454500352
    iterations: 77
    delta: 0.0556313446822
    ----------------------------------------------------------

    ---------------- Registers for rank 1 -------------------
    world_delta: 0.115454500352
    iterations: 77
    delta: 0.0130501901041
    ----------------------------------------------------------

    ---------------- Registers for rank 2 -------------------
    world_delta: 0.115454500352
    iterations: 77
    delta: 0.0467729655656
    ----------------------------------------------------------
    
and again::

    > python pupy_readregisters.py /var/folders/Yb/YbuXflfJFemHX4JTvqTG8U+++TI/-Tmp-/pupyShSSrS
    ---------------- Registers for rank 0 -------------------
    world_delta: 0.0103912816469
    iterations: 144
    delta: 0.000598715003548
    ----------------------------------------------------------

    ---------------- Registers for rank 1 -------------------
    world_delta: 0.0103912816469
    iterations: 144
    delta: 0.0014827060862
    ----------------------------------------------------------

    ---------------- Registers for rank 2 -------------------
    world_delta: 0.0103912816469
    iterations: 144
    delta: 0.00830986055712
    ----------------------------------------------------------

