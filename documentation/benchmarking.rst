.. _benchmarking: 

Benchmarking your pupyMPI runs
===================================

.. module:: mpi.benchmark
.. autoclass:: Benchmark 
   :members: __init__, get_tester, flush
.. autoclass:: Test
   :members: start, stop, discard

A full example 
--------------------------------------

The file layout
--------------------------------------
The written files are simple CSV files writting with a custom extension for
the builtin ``csv`` module. An example of a file written could be as follows::

    > cat ...

This format is readable by pupyplot but if custom solutions is needed it is
also possible to either extend pupyplot or simply read the .csv files with the
``csv`` module. 


Packing your files for later plotting
--------------------------------------


