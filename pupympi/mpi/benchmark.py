# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
#
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
# Make sure the with keyword is available
from __future__ import with_statement


"""
Benchmarking documentation
"""

from csv import DictWriter
from datetime import datetime
import time

class BenchmarkWriter(DictWriter):
    """
    Writes benchmark data into a file without any timing logic
    etc. You should probably not use this directly but simply
    rely on the timing class to write using this class.

    This class inherits from the builtin CSV writer but fixes
    some arguments in initializing. This is done to ensure pupyplot
    can handle data correctly.
    """
    def __init__(self, filehandle):
        # This will not work in Python 3 as we use oldstyle classes. Hopefully the csv module.
        self.fieldnames = ["datasize" ,"repetitions", "total_time" ,"avg_time", "min_time", "max_time", "throughput", "nodes", "testname", "timestamp"]
        DictWriter.__init__(self, filehandle, self.fieldnames, extrasaction='ignore')

        # Write a headerow
        header = {}
        for e in self.fieldnames:
            header[e] = e
        self.writerow(header)

    def write(self, *args, **kwargs):
        """Enable use to write the paramters in the method call instead of creating a dict. """
        self.writerow(kwargs)

class Benchmark(object):
    """
    A minimal benchmarking utility working very well with pupyplot for plotting different tests and runs. The
    class is initialized with an optional communicator instance and datasize. The communicator and datasize
    is used as defaults for the parameters in the :func:`get_tester` method documented below.

    The ``roots`` parameter is used to indicate which(s) ranks in respect to the given communicator should
    do the benchmarking. The paramter defaults to rank 0, but can be set to any given rank in the communicator
    or even multiple. It is valid to enter both an integer or iterable of integers.

    Use the :func:`flush` method when all the run has been timed and the data should be written to the disk.

    .. versionadded:: 0.9.5
    """
    def __init__(self, communicator, datasize=None, roots=1):
        self.datasize = datasize
        self.communicator = communicator
        self.testers = {}

        if not hasattr(roots, "__iter__"):
            roots = [roots]
        self.roots = roots

    def get_tester(self, testname, procs=None, datasize=None):
        """
        Creates and track a :class:`Test` instance with the given parameters.

        .. note:: You should never create a `Test` instance directly but use this method as the class with be registered and written to the filesystem with :func:`flush`.

        """
        if procs is None:
            procs = self.communicator.size()

        if datasize is None:
            datasize = self.datasize

        if procs not in self.testers:
            self.testers[procs] = {}

        if datasize not in self.testers[procs]:
            self.testers[procs][datasize] = {}

        create = testname not in self.testers[procs][datasize]
        if create:
            self.testers[procs][datasize][testname] = Test(testname, procs, datasize)

        return self.testers[procs][datasize][testname], create

    def flush(self, flushdir):
        """
        Write the gathered data into several .csv files. The names for the format will include the test name and the number of involving processors. This is done accordingly to
        pupymark which is the internal benchmarking suite for pupyMPI. The files will also include a timestamp of the benchmark. This means that two benchmarks will not overwrite
        each others files unless the time and data is exactly the same which is very unlikely.

        The files will be saved in the LOGDIR folder, defaulting to ``user_logs``. See the documentation for :ref:`mpirun` for more information about settings the default log dir.

        .. note:: This method will not close any running times, so these will not be included in the flushed output.
        """
        if self.communicator and self.communicator.rank() not in self.roots:
            return

        # Run through the gathered data sort it
        for procs in self.testers:
            tests = {}
            for datasize in self.testers[procs]:
                for testname in self.testers[procs][datasize]:
                    if testname not in tests:
                        tests[testname] = []

                    # Append the data to the list making it easier to sort
                    tests[testname].append(
                        (datasize, self.testers[procs][datasize][testname])
                    )

            for testname in tests:
                testlist = tests[testname]

                if flushdir:
                    filename = flushdir
                else:
                    filename = self.communicator.mpi.logdir

                filename += "/pupymark.%s.%dprocs.%s.csv" % (testname, procs, datetime.now())
                filename = filename.replace(" ", "_").replace(":", "-")

                fh = open(filename, "w")
                bw = BenchmarkWriter(fh)
                for t in testlist:
                    datasize, t_obj = t
                    bw.writerow(t_obj.get_dict())
                fh.close()

class Test(object):
    def __init__(self, testname, procs, datasize):
        self.name = testname

        # For timing
        self.started_at = None
        self.times = []

        self.procs = procs
        self.datasize = datasize

    def get_dict(self):
        sum_time = sum(self.times) * 1000
        min_time = min(self.times) * 1000
        max_time = max(self.times) * 1000
        avg_time = sum_time*1000 / len(self.times)

        throughput = -42
        if self.datasize > 0:
            throughput = self.datasize*1024*1024 / (avg_time/1000)

        return {
            'datasize' : self.datasize,             # Bytes
            'total_time' : sum_time,                # Mili seconds
            'avg_time' : avg_time,                  # Micro seconds
            'min_time' : min_time,                  # Micro seconds
            'max_time' : max_time,                  # Micro seconds
            'throughput' : throughput,              # MB / sec
            'repetitions' : len(self.times),        # Int
            "nodes" : self.procs,                   # Int
            "testname" : self.name,                 # String
            "timestamp" : datetime.now(),           # Timestamp
        }

    def start(self):
        """
        Starts the timer for a new run. The time here only has effect when the :func:`stop`
        is called. The timer uses simple calls to the builtin :func:`time.time` module and will inherit
        the same accuracy.

        Calling this method two times without calling :func:`stop` in between will
        raise an Exception. If you do not wish to use the started timing use the :func:`discard`
        method::

            bw = Benchmark()
            tester = bw.get_tester( ... )
            tester.start()
            tester.stop() # First record
            tester.start()
            tester.start() # Raise Exception

        If you intent to plot the benchmarked data with pupyplot you don't need to think about stray data points. There are different utilities for handling and plotting this.
        """
        if self.started_at is not None:
            raise Exception("Timer already started. Please remmeber to class end() when a run completes")

        self.started_at = time.time()

    def stop(self):
        """
        Stop the current timer and record the timing for later flushing.
        """
        time_diff = time.time() - self.started_at
        self.times.append(time_diff)
        self.discard()

    def discard(self):
        """
        Stop the current timer without recording the data.
        """
        # Clear for another run
        self.started_at = None

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, tb):
        self.stop()
