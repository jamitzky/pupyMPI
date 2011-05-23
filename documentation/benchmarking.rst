.. _benchmarking: 

Benchmarking your pupyMPI runs
===================================

This page describes how to benchmark you pupyMPI programs. This layer might
seem very lightweight and indeed it is. The power comes from the easy
integration with :ref:`the plotting tool called pupyPlot <plot>`. 

.. module:: mpi.benchmark
.. autoclass:: Benchmark 
   :members: __init__, get_tester, flush
.. autoclass:: Test
   :members: start, stop, discard

.. _stencil: 

A full example 
--------------------------------------
Take a look at the example stencil solver located in
``benchmark/jacobi/stencil_solver.py``. If we cut through the clutter the
essisial solving loop look like this::

    def stencil_solver(local,epsilon):
        """
        The function receives a partial system-matrix including ghost rows in top and bottom
        """
        W, H = local.shape
        maxrank = size - 1
        
        work = numpy.zeros((W-2,H-2)) # temp workspace
        
        cells = local[1:-1, 1:-1] # interior
        left  = local[1:-1, 0:-2]
        up    = local[0:-2, 1:-1]
        down  = local[2:  , 1:-1]    
        right = local[1:-1, 2:  ]

        delta = epsilon+1
        counter = 0
        while epsilon<delta:
            if rank != 0:
                local[0,:] = world.sendrecv(local[1,:], dest=rank-1)
            if rank != maxrank:
                local[-1,:] = world.sendrecv(local[-2,:], dest=rank+1)
            work[:] = (cells+up+left+right+down)*0.2
            delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)
            cells[:] = work
            counter += 1
            
        if rank == 0:
            print "rank %i done, in %i iterations with final delta:%s (sample:%s)" % (rank, counter, delta, cells[10,34:42])

Before a number of optimization steps are implemented benchmark data should be
collected and optimization can be validated though plots. The benchmarking
should not be manual as this will take a long time and possible be very error
phrone. Instead the above benchmarking library is inserted::

    def stencil_solver(local,epsilon):
        """
        The function receives a partial system-matrix including ghost rows in top and bottom
        """
        from mpi.benchmark import Benchmark
        
        # We define the data size as the product of W and H times the byte size of the inner
        # data type. 
        datasize = height*width*local.dtype.itemsize
        bw = Benchmark(world, datasize=datasize)
        
        # We wish to benchmark the complete solving (identifier complete), the edge exchange
        # identifier (edge) and the delta calculation (identifier delta).
        bw_complete, _ = bw.get_tester("complete")
        bw_edge, _ = bw.get_tester("edge")
        bw_delta, _ = bw.get_tester("delta")
        
        bw_complete.start()
        
        W, H = local.shape
        maxrank = size - 1
        
        work = numpy.zeros((W-2,H-2)) # temp workspace
        
        cells = local[1:-1, 1:-1] # interior
        left  = local[1:-1, 0:-2]
        up    = local[0:-2, 1:-1]
        down  = local[2:  , 1:-1]    
        right = local[1:-1, 2:  ]

        delta = epsilon+1
        counter = 0
        while epsilon<delta:
            bw_edge.start()
            if rank != 0:
                local[0,:] = world.sendrecv(local[1,:], dest=rank-1)
            if rank != maxrank:
                local[-1,:] = world.sendrecv(local[-2,:], dest=rank+1)
            bw_edge.stop()
            work[:] = (cells+up+left+right+down)*0.2
            
            bw_delta.start()
            delta = world.allreduce(numpy.sum(numpy.abs(cells-work)), MPI_sum)
            bw_delta.stop()
            
            cells[:] = work
            counter += 1
            
        if rank == 0:
            print "rank %i done, in %i iterations with final delta:%s (sample:%s)" % (rank, counter, delta, cells[10,34:42])

        bw_complete.stop()

        # Flush the benchmarked data to files
        bw.flush()

Now we are ready to benchmark some runs. We automate the run by writing the
following simple shell script::

    for n in 2 4 8 16 32
    do
        for h in 200 500 1000 1500 2000
        do
            bin/mpirun.py -c $n benchmark/jacobi/stencil_solver.py -- $h $h 40000
        done
    done

Looking at the ``user_logs`` directory shows that there are indeed benchmark
data::

    $ ls -1 user_logs/*.csv | head
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.077206.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.080101.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.084135.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.090834.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.105511.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.107864.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.108015.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.108619.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.109679.csv
    user_logs/pupymark.complete.16procs.2011-05-22_13-25-55.111018.csv

The file layout
--------------------------------------
Looking at one of the files outputs::

    $ cat user_logs/pupymark.complete.2procs.2011-05-22_13-41-45.303646.csv 
    datasize,repetitions,total_time,avg_time,min_time,max_time,throughput,nodes,testname,timestamp
    160000,1,8362.04099655,8362040.99655,8362.04099655,8362.04099655,20063541.9115,2,complete,2011-05-22 13:41:45.304223


This format is readable by pupyplot but if custom solutions is needed it is
also possible to either extend pupyplot or simply read the .csv files with the
``csv`` module. 

To few or to many .csv files
----------------------------------------------------
If you cant see any files, you might have a problem with the LOGDIR parameters
sent to mpirun.py. If you specificed this parameter you should look into the
documentation to see what you did wrong. If you did not, your .csv files
should be located in the ``user_logs`` directory. 

Do you see more output files than you would expect? The ``roots`` parameter
is used to set which ranks should write the final csv files to the file
system. This will default to only rank 0, so if you supply a bigger list, you
will see a lot of files.

Benchmarking with fewer lines
----------------------------------------------------
The ``Test`` objects suppor the ``with`` keyword for faster staring and
stopping the timings. Look at this regular benchmarking code::

    bw_edge, _ = bw.get_tester("edge")
    bw_edge.start()

    # ... calculate something..

    be_edge.stop()

This is not complex but some care must be taken to ensure that the ``stop``
method is always called indifferent of when you exit a function etc. This is
much like the problems people face when working with locks. The above code can
be made cleaner and safer like this::

    bw_edge, _ = bw.get_tester("edge")
    with bw_edge:
        # ... calculate something..

Note that the above code will record the time no matter what happens. If you
want to break the control flow without recording the running timer you need to
call the discard function.::

    bw_edge, _ = bw.get_tester("edge")
    with bw_edge:
        # ... calculate something..
        # something bad happend here. We will return right away but
        # discard the timing first.
        bw_edge.discard()
        return

Packing your files for later plotting
--------------------------------------
The benchmarked files should be placed in a directory per code version. This
will allow seemless integration with pupyPlots ``readdata.py`` utility.

