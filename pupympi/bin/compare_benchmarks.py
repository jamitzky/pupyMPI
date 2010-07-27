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
        
    def get_types(self):
        return self.data.keys()
        
    def get_data(self, run_type, procs=None, datasize=None):
        data = self.data[run_type]
        
        if procs:
            data = data[procs]
            
        if datasize:
            data = data[datasize]
            
        return data
        
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
    parser.add_option("--build-folder", default="result", dest="build_folder", help="Name the folder all the result files should be places. This will include a Makefile, a number of data files, gnuplot files etc. If no argument is given the script will try to create a <result> folder in the current directory")
    options, args = parser.parse_args()
    
    if len(args) <= 1:
        parser.error("You should provide at least two folders with benchmarks data for comparison.")
    
    return args, options

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
            
def draw_scatter(gather, folder):
    """
    This function will output a lot of gnuplot data
    to be manualle executed. This gives you the option
    to make last minute (or second) changes in captions
    etc. Face it.. captions should be manually 
    written
    """
    
    def get_x_tics(data):
        data = list(set(data))
        data = map(int, data)
        data.sort()
        
        mm = 1024
        final_data = []
        for s in data:
            size = ""
            if s < mm:
                size = "%dB" % s 
            elif s < mm*mm:
                k = s / mm
                size = "%dKB" % k
            else:
                k = s / (mm*mm)
                size = "%dMB" % k
                
            final_data.append('"%s" %d' % (size, s))
        return final_data
    
    def get_y_tics(max_value):
        tics = ['"0us" 0']
        current = 1
        
        while current < max_value:
            # add the current time level to the tics
            if current < 1000:
                tics.append('"%2.fus" %d' % (current, current))
            elif current < 1000000:
                c = current / 1000.0
                tics.append('"%2.fms" %d' % (c, current))
            else:
                c = current / 1000000.0
                tics.append('"%2.fs" %d' % (c, current))
            current *= 10
        return tics
    
    # Right now se just test with a single run type. 
    for run_type in gather.get_types():
        data = gather.get_data(run_type)
        data_sizes = data.values()[0].keys()
        x_labels = get_x_tics(data_sizes)
        max_time = 0
        # Flush the data points to a file.
        files = []
        
        for nc in data.keys():
            filename = "%s_%d.dat" % (run_type, nc)
            title = "%s for %d nodes" % (run_type, nc)
            f = open(folder + "/" + filename, "w")
            files.append( (filename, title) )
            for datasize in data[nc].keys():
                values = data[nc][datasize]
                
                # Throw the throughput away
                values = [v[0] for v in values]
                
                for value in values:
                    if value > max_time:
                        max_time = value
                    print >> f, "%d %f" % (datasize, value)
            f.close()
        
        y_labels = get_y_tics(max_time)
        
        # At some point we can make a smart filename here.
        of = open("%s/%s.gnu" % (folder, run_type), "w")
        
        # plot the data.
        print >> of, "set terminal png nocrop enhanced size 800,600"
        print >> of, 'set output "%s.png"' % run_type
        print >> of, 'set title "%s plot"' % run_type
        print >> of, 'set xlabel "Data size (MB)"'
        print >> of, 'set ylabel "Wallclock in (sec)'
        print >> of, 'set xtics (%s)' % ", ".join(map(str, x_labels))
        print >> of, 'set ytics (%s)' % ", ".join(map(str, y_labels))
        print >> of, "set log x"
        print >> of, "set log y"

        print >> of, 'set style line 1  linetype 1 linecolor rgb "red"  linewidth 1.000 pointtype 1 pointsize default'
        print >> of, 'set style line 2  linetype 2 linecolor rgb "orange"  linewidth 1.000 pointtype 2 pointsize default'
        print >> of, 'set style line 3  linetype 3 linecolor rgb "yellow"  linewidth 1.000 pointtype 3 pointsize default'
        print >> of, 'set style line 4  linetype 4 linecolor rgb "green"  linewidth 1.000 pointtype 4 pointsize default'
        print >> of, 'set style line 5  linetype 5 linecolor rgb "cyan"  linewidth 1.000 pointtype 5 pointsize default'
        print >> of, 'set style line 6  linetype 6 linecolor rgb "blue"  linewidth 1.000 pointtype 6 pointsize default'
        print >> of, 'set style line 7  linetype 7 linecolor rgb "violet"  linewidth 1.000 pointtype 7 pointsize default'
        
        i = 0
        plot_str = 'plot '
        plot_strs = []
        for p in files:
            filename, title = p
            i += 1
            plot_strs.append(' "%s" ls %d title "%s"' % (filename, i, title))
            
        plot_str += ", ".join(plot_strs)
        print >> of, plot_str
        
        of.close()
            
def write_gnuplot_makefile(folder_name):
    fh = open(folder_name+"/Makefile", "w")
    
    print >> fh, "all:"
    print >> fh, "\tgnuplot *.gnu\n"
    print >> fh, "clean:"
    print >> fh, "\trm *.png"
    fh.close()            

if __name__ == "__main__":
    # Handle arguments etc. 
    folders, options = options_and_arguments()
    
    # Parse benchmark data for each folder into an internal structure. 
    run_folders = find_runs(folders)
    
    # Initialize a gather object. This object will hold all data
    # and make it possible to extract it later
    gather = DataGather()
    
    data = parse_benchmark_data(run_folders, gather)
    
    # Ensure we have the output folder
    output_folder_name = options.build_folder
    import os
    try:
        os.mkdir(output_folder_name)
    except OSError:
        pass
    
    # Were we should actually look if we're using gnuplot
    # and only write the makefile if so.
    write_gnuplot_makefile(output_folder_name)
    
    # If we should choose to implement further output functions we should
    # add an options above and select an output function here.
    def timer_wrapper():    
        draw_scatter(gather, output_folder_name)
    
    # Stop the timing and say goodbye.
    from timeit import Timer
    t = Timer(timer_wrapper)
    t = t.timeit(number=1)
    
    print "Goodbye. We parsed %d benchmark folders in %.2f seconds" % (len(folders), t)
