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
import os, sys, glob, csv

mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

from mpi import constants

class DataGather(object):
    
    def __init__(self):
        self.row_counter = 0
        self.data = {}
    
    def add_data(self, run_type, procs, datasize, time, throughput):
        # clean the run_type name
        if run_type.startswith("test_"):
            run_type = run_type[5:]
            
        # Cast data to correct values
        procs = int(procs)
        datasize = int(datasize)
        time = float(time)
        throughput = float(throughput)
        
        # Adding data is not so nice. There is a bunch of testing if
        # indexes is already there. Sorry.
        if run_type not in self.data:
            self.data[run_type] = {}
            
        if procs not in self.data[run_type]:
            self.data[run_type][procs] = {}
            
        if datasize not in self.data[run_type][procs]:
            self.data[run_type][procs][datasize] = []
            
        self.data[run_type][procs][datasize].append( (time, throughput))
        
    def __repr__(self):
        # Find some key information
        second_keys = []
        for f in self.data.values():
            second_keys.extend(f.keys())
        second_keys = list(set(second_keys))
        second_keys.sort()
        
        third_keys = []
        for f in self.data.values():
            for k in f.values():
                third_keys.extend(k.keys())
        third_keys = list(set(third_keys))
        third_keys.sort()
        
        st = "<<<Gather object:\n"
        st += "\t --> first level keys: %s\n" % ", ".join(map(str,self.data.keys()))
        st += "\t\t --> second level keys: %s\n" % ", ".join(map(str, second_keys))
        st += "\t\t\t --> third level keys: %s\n" % ", ".join(map(str, third_keys))
        st += ">>>\n"
        return st

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

def find_runs(folders):
    runs = []
    for folder in folders:
        runs.extend(glob.glob(folder + "collective[0-9]*"))
        runs.extend(glob.glob(folder + "single[0-9]*"))
        
    return runs

def parse_benchmark_data(run_folders, gather):
    for f in run_folders:
        files = glob.glob(f + "/*.csv")
        for f in files:
            reader = csv.reader(open(f))
            for row in reader:
                # Some basic sanitize
                if len(row) < 2:
                    continue
                
                try:
                    # Remove comments
                    fc = row[0].strip()
                    if fc.startswith("#"):
                        continue
                    
                    # Remove headers
                    try:
                        int(row[0])
                    except:
                        continue
                    
                except:
                    pass
                
                # Unpack data
                datasize = row[0]
                time_p_it = row[3]
                throughput = row[4]
                procs = row[5]
                run_type = row[6]
                gather.add_data(run_type, procs, datasize, time_p_it, throughput)
            
def sanitize_data(data):
    return data

def write_html_and_js(data):
    pass

if __name__ == "__main__":
    # Handle arguments etc. 
    folders = options_and_arguments()
    
    # Parse benchmark data for each folder into an internal structure. 
    run_folders = find_runs(folders)
    
    # Initialize a gather object. This object will hold all data
    # and make it possible to extract it later
    gather = DataGather()
    
    data = parse_benchmark_data(run_folders, gather)
    
    print gather
    
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
