#!/usr/bin/env python2.6
#
# Copyright 2010 Rune Bromer, Frederik Hantho, Jan Wiberg and Asser Femoe
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
#

# Allow the user to import mpi without specifying PYTHONPATH in the environment
import os, sys
mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

from mpi import constants

def options_and_arguments():
    from optparse import OptionParser
    
    usage = """usage: %prog [options] folder1 folder2 ... folderN
    
    <<folder1>> to <<folderN>> should be folders containing benchmark 
    data for comparison. You should provide at least 2 folders."""   
    
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))
    _, args = parser.parse_args()
    
    if len(args) <= 1:
        parser.error("You should provide at least two folders with benchmarks data for comparison.")
    
    return args

def parse_benchmark_data(folders):
    import glob
    
    folder_contents = []
    for folder in folders:
        cluster_runs = glob.glob(folder + "*")
        
        # Only folders.
        
        folder_contents.update(cluster_runs)
    
    print folder_contents

    
    data = None
    
    return data

def sanitize_data(data):
    return data

def write_html_and_js(data):
    pass

if __name__ == "__main__":
    # Handle arguments etc. 
    folders = options_and_arguments()
    
    # Parse benchmark data for each folder into an internal structure. 
    data = parse_benchmark_data(folders)
    
    data = sanitize_data(data)

    # If we should choose to implement further output functions we should
    # add an options above and select an output function here.
    def timer_wrapper():    
        write_html_and_js(data)
    
    # Stop the timing and say goodbye.
    from timeit import Timer
    t = Timer(timer_wrapper)
    t = t.timeit(number=1)
    
    print "Goodbye. We parsed %d benchmark folders in %.2f seconds" % (len(folders), t)
    
    
