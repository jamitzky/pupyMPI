.. _plot: 

pupyPlot - Visualization for benchmarked data
==============================================
This page describes the tools and methods for plotting benchmark data
collected with the :ref:`builtin benchmarker <benchmarking>`. The source format
for plotting can also be other ``.csv`` files but pupyPlot put special
attention to some columns and expect data in specific units so explore the
possiblities at your own risk. 

.. versionadded:: 0.9.5

Introduction to the concepts of pupyPlot
-----------------------------------------------------------------------------
The steps you need to go though before creating an actual plot are created
from an assumption that you will need to plot the same data several times.
This means that a script called ``readdata.py`` is called first to parse and
normalize the benchmarked data before plotting. Hereafter some headlines and
naming can be done before the actual plotting takes place. 

pupyPlot is written allowing users to compare different benchmark data, ie.
plotting some version of a code base against a different version. This allows
the users to see how their changes affected performance. When the number of
axis grow this is not an easy task to do by hand. As it is normal for people
to tag their releases we use the term ``tag`` for any given version of a code
base. 

.. note:: Even though pupyPlot is written for comparing different tags it can
    also be used as a simple plotting utility for reports etc. We try to
    strike a balance between automation and customization and you almost
    cirtainly will need to alter the resulting ``.gnu`` files if you do not
    compare several tags.

Parsing data into a simple structure - ``readdata.py``
-----------------------------------------------------------------------------
Before you use this utiltity you should organize your benchmark data into
folders, one folder per tag. Each folder should contain the benchmarked
``.csv`` files. Let's assume that you wrote the :ref:`stencil solver we used
as an example in the benchmarking section <stencil>`. You are not quite
pleased with the performance of the 
:func:`allreduce <mpi.communicator.Communicator.allreduce>` operation 
calculating the stop condition, so you alter that part to use the non blocking
collective counterpart 
:func:`iallreduce <mpi.communicator.Communicator.iallreduce>` and test out of
order if the delta is small enough. The benchmarked files are stored in:

 * ``/home/yourusername/benchmarkdata/blocking/``
 * ``/home/yourusername/benchmarkdata/nonblocking/``

Alone writing both directories takes up a lot of space. Looking at the usage
of the ``readdata.py`` script::

    $ ./readdata.py --help
    Usage: readdata.py [options] folder1 folder2 ... folderN handlefile

            <<folder1>> to <<folderN>> should be folders containing benchmark
            data for comparison.

    Options:
    --version            show program's version number and exit
    -h, --help           show this help message and exit
    -u, --update-output  Update the output file with new contents. Default will
                        overwrite the file

The ``handlefile`` is the file that will end up with the collected benchmark
data:: 

    $ ./readdata.py /home/yourusername/benchmarkdata/blocking/
        /home/yourusername/benchmarkdata/nonblocking/ plotdata.plk

The ``.plk`` extension is home brewed for *pickled data*. Notice that the
script did not only create a file called ``plotdata.pkl`` but also the file
named ``plotdata.pkl.tagmapper``. By editing this file it is possible to
rename the tags from their simple folder names to something nicer that should
be used in the plots. For example, the original content::

    something

could be changed to::

    something else

That will change the tag names in every plot that use the ``plotdata.pkl``. 

Common grounds for the avilable plots
-------------------------------------------------------------------------------
Most of the available plotting scripts - described below - have a number of
common command line arguments. This include everything from selecting the
proper data on each axis to data filtering and minipulation. This section will
not give an extensive overview and description of these paramters, but the
scripts will not resue arguments for different purposes. There are some key
elements that bears mention.

**Data filtering:** There are several different ways to filter the parsed data
if you only want to plot a subset of this. There are some very expressive ways
to filter specific important paramters and a low level filtering method:

``--filter-test=testname1,testname2``
    Filters the data to only contain data with identifiers *testname1* or
    *testname2*. The identifiers is the names of the test you give as argument
    to the :func:`get_tester <mpi.benchmark.Benchmark.get_tester>` function.

``--y-filter=`` and ``--x-filter=``
    Allows you to filter the data you choose on either axis according to some
    predefined filers. Currently only the *zero* filter is available that
    filters elements that evaluate to false in Python. 

``--raw-filters=``
    This allows you to describe filters that apply to any given column in the
    parsed data files. Currently it is only possible to filter according to
    *is equal to* or *is not equal to*, but this can be extended in the
    future. It is possible to give multiple values for each filter. For
    example a filter that only allows data for runs with 8 and 32 procsessors
    for a test called mytest can be written as
    ``--raw-filters=nodes:8,3;testname=mytest``

.. note:: Be careful when filtering the data. Remember what you need to show
    be sure to document the data selection. It is often easy to filter data to
    match a wanted situation than to explain why the data does not fit into
    the grand plan. 

**Data aggregation:** It is not uncommon to end up with multiple values for a
single x coordinate. In many cases it is actually a very good thing as this
menas you have pleanty of benchmark data. In many plots - scatter plots being
the exception - you do know want to plot every data point but pick a
representative (or calculate one). There are not only one valid solution for
this, so pupyPlot comes with several options:

* ``min``
* ``max``
* ``avg``
* ``stddiv``

Line plots - ``line.py`` 
-------------------------------------------------------------------------------

Scatter plots - ``scatter.py``
-------------------------------------------------------------------------------

Scale or speedup plots - ``scale.py``
-------------------------------------------------------------------------------


Plot automation
-----------------------------------------------------------------------------
It was clear from the start that a single utility could not be abstract and
configurable enough for suit all needs. When the benchmarked system grows in
complexity the authors needs to plot more and more which pupyPlot can handle
directly. We chose to implement all the utilities as simple scripts with a
number of command line arguments. This makes it quite easy to automate
extensive plotting with Makefiles or simple shell scripting. 


Remove temporary files - ``cleanup.py``
-----------------------------------------------------------------------------
If something goes wrong or you have chosen to keep the tempory files and need
them cleaned up the ``cleanup.py`` script can help you. 

.. warning:: Please note that this script does not know which files pupyplot
    have created and will simply delete all ``.gnu``, ``.data`` and ``.eps``
    files. For this reason it makes a lot of sense to move your finished data
    out of the directory you are working in.

