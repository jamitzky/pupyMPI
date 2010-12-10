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

