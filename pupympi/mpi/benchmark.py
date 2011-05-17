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


