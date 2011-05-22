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

