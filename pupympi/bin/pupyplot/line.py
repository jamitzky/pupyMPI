#!/usr/bin/env python
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

import sys, os, glob

pupyplotpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
binpath = os.path.dirname(os.path.abspath(pupyplotpath))
mpipath = os.path.dirname(os.path.abspath(binpath))

sys.path.append(mpipath)
sys.path.append(pupyplotpath)
sys.path.append(binpath)

from mpi import constants
from mpi.logger import Logger

from pupyplot.lib.cmdargs import plot_parser, parse
from pupyplot.lib.tagmapper import get_tag_mapping
from pupyplot.parser.handle import Handle, DataSupplier, DataAggregator
from pupyplot.gnuplot import LinePlot

if __name__ == "__main__":
    # Receive the parser and groups so we can add further elements 
    # if we want
    parser, groups = plot_parser()
    
    # Parse it. This will setup logging and other things.    
    options, args = parse(parser)
    
    Logger().debug("Command line arguments parsed.")
    
    # Object creation, used to keep, filter, aggregate, validate data.
    handle = Handle(args[0])
    
    tag_mapper = {}
    if options.tag_mapper:
        tag_mapper = get_tag_mapping(options.tag_mapper)
    
    # Create a DataSupplier object from the data. This is used
    # to extract and filter the data.
    ds = DataSupplier(handle.getdata())
    
    # It should be possible to limit the tests to one single test. how should
    # this be one. 
    all_tests = ds.get_tests()
    for testname in all_tests:
        if testname != "Reduce":
            continue # debug
        
        lp = LinePlot(testname, title=testname, xlabel=options.x_data, ylabel=options.y_data, keep_temp_files=True)
        
        tags = ds.get_tags()
        plot_strs = []
        i = 0
        for tag in tags:
            # Extract the data from the data store.
            xdata, ydata = ds.getdata(testname, tag, options.x_data, options.y_data, filters=[])
            
            # Aggregate the data. 
            da = DataAggregator(ydata)
            ydata = da.getdata(options.y_data_aggr)
            
            # Write a datafile
            datafile = lp.write_datafile("data%d" % i, xdata, ydata)
            
            # Write the plot commands. 
            plot_strs.append("'%s' with linespoints title 'plot %d'" % (datafile, i))
            
            # Increment a general counter
            i += 1
            
        # Write the plot command to the handle.
        print >> lp.handle, "plot " + ", ".join(plot_strs)
        
        lp.plot()
        lp.close()
            
        