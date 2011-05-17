#
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
from csv import DictWriter
from datetime import datetime

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
        
    def write(self, *args, **kwargs):
        """Enable use to write the paramters in the method call instead of creating a dict. """
        self.writerow(kwargs)
        
class Benchmark(object):
    def __init__(self, communicator=None):
        self.communicator = communicator
        self.testers = {}
       
    def get_tester(self, testname, procs=None):
        if procs is None:
            if self.communicator is not None:
                procs = self.communicator.size()
            else:
                procs = 0

        if procs not in self.testers:
            self.testers[procs] = {}

        create = testname not in self.testers[procs]
        if create:
            self.testers[procs][testname] = Test(testname)
        
        return self.testers[procs][testname], create
    
    def flush(self):
        pass
             
class Test(object):
    def __init__(self, testname):
        self.name = testname
        
        # For timing
        self.started_at = None
        
        self.times = []
        
    def start(self):
        if self.started_at is not None:
            raise Exception("Timer already started. Please remmeber to class end() when a run completes")
        
        self.started_at = time.time()
        
    def end(self):
        time_diff = time.time() - self.started_at
        self.times.append(time_diff)
        
        # Clear for another run
        self.started_at = None
        
if __name__ == "__main__":
    b = Benchmark()
    
    
    for _ in range(10):
        t, created = b.get_tester("allreduce", 3)
        print "created", created
        import random
        import time
        t.start()
        r = random.randint(1, 5)
        print "Sleeping for %d seconds" % r
        time.sleep(r)
        t.end()
        
        print t
        print t.times
        print len(t.times)