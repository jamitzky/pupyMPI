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

# FIXME: The documentation does not seem do consider that there are
# multiple tests in the data. Maybe we should define the result to
# be a dict containing all the tests?
#
"""
This module contains a collection of classes to manipulate and otherwise
manage the parsed data. The code is divided into 3 seperate classes to
avoid complex 'business' logic mixed with regular data handling. The
classea have their own individual responsability:

    **Handle**:
        Is a very thin wrapper around the pickle module saving and reading
        the parsed data to and from a file.
    **DataSupplier**:
        After reading the data the DataSupplier can be used to extract
        data in a more plotable format. This makes it a lot easier to
        avoid knowing to much about the data layout in the first place
        but simply care about the plot methods. The format of the data will
        be something like this::

        ds = DataSupplier(handle) # handle of type Handle.

        # extract a list of the minimum times for each node count
        nodes, times = ds.getdata("nodes", "mintime")

        # data layout
        [1, 2, 4, 8, 16, 32]     # contents from nodes
        [ [t11, t12, t13], [t21, t22, t23], [t31, t32, t33] ... ] # timings.

    Data in this format can be added

**DataAggregator**:
    Aggregates the data according to some functions. The returned
    is N lists of size M where N is the the number of aggregate
    functions. M is the number of indexes. Taking the above
    example we continue:

        da = DataAggregator()
        agg = da.aggregate(times, max)

        # data layout
        [1, 2, 4, 8, 16, 32]     # contents from nodes (not changed)
        [ max(t11, t12, t13), max(t21, t22, t23), max(t31, t32, t33) ... ] # timings.
    
    Several plots should be made by simply using this function multiple times.
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

from os import path
from pupyplot.lib.aggregate import find_function

class Handle(object):
    """
    The main way to interact with the handle file. It is possible to
    add / remove / edit data to the file and have it written to the
    file system.
    """

    def __init__(self, filename='parsed.pickled', dataobj=[]):
        self.dataobj = dataobj
        self.filename = filename

        # Load the file if it exists on the disk
        self.reload()

    def save(self):
        pickle.dump(self.dataobj, open(self.filename, "w"), pickle.HIGHEST_PROTOCOL)

    def reload(self):
        if Handle.valid_handle_file(self.filename):
            self.dataobj = pickle.load(open(self.filename, "r"))
            
    def getdata(self):
        return self.dataobj

    @classmethod
    def valid_handle_file(cls, filename):
        if path.isfile(filename):
            try:
                pickle.load(open(filename, "r"))
                return True
            except Exception, e:
                print e
                pass
            
        return False
    
class DataSupplier(object):
    """
    This class can suply the parsed data in a way that is suitable
    for plotting and aggregating. It has as its main features:

        * While keeping all the data internally it it possible to
          select an index parameter and value parameter. This mean
          that the :func:`getdata` function will return a list of
          index parameters and a list of list with values maching
          the index list.
        * Filtering. It is possible to add a number of filters to
          the :func:`getdata` call. This will filter the data before
          returning it.

    This class will not aggregate the data as there is a seperate
    class called :ref:`DataAggregator` for this.
    """
    def __init__(self, data):
        self.data = data
        
        # Internal list to keep the tests.
        self.tests = self._find_test_names()
        
    def _find_test_names(self):
        all_tests = set([])
        [all_tests.add(item[1]) for item in self.data]
        return list(all_tests)
    
    def get_tests(self):
        return self.tests
    
    def get_raw_test_data(self, testname):
        filtered_data = []
        
        for item in self.data:
            if item[1] == testname:
                filtered_data.append(item)
        
        return filtered_data
    
    def _get_pos(self, label):
        labels = ["tag", "runtype", "datasize", "avg_time", "throughput", "min_time", "max_time", ]
        for i in range(len(labels)):
            if label == labels[i]:
                return i
              
    def getdata(self, testname, xdata, ydata, filters=[]):
        if testname not in self.tests:
            raise Exception("No test called %s" % testname)

        filtered_data = self.get_raw_test_data(testname)
        
        # Run the filters on the data
        for func in filters:
            filtered_data = filter(func, filtered_data)

        # Find the position of each data label. This is used to         
        x_pos = self._get_pos(xdata)
        y_pos = self._get_pos(ydata)
        # extract the data later.
                
        # A structure to keep the filtered data. This will not 
        # be returned direcly.
        data = {}
        for data_item in filtered_data:
            x_data = data_item[x_pos]
            y_data = data_item[y_pos]
            
            if x_data not in data:
                data[x_data] = []
            
            data[x_data].append(y_data)
            
        keys = data.keys()
        keys.sort()
        
        values = []
        for k in keys:
            values.append(data[k])
        
        return keys, values
        
class DataAggregator(object):
    """
    This class contains a simple getdata function that
    takes data after a DataSupplier have extracted and
    filtered it. It then performs aggregations changing
    the format of the data to be at a deeper level.

    The default aggregator is the identify function,
    """
    def __init__(self, data):
        self.data = data
    
    def getdata(self, aggregator):
        aggregator = find_function(aggregator)
                
        return [aggregator(datum) for datum in self.data]
