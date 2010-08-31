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
import os, sys, glob, csv, re, time, subprocess

mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

from mpi import constants

def options_and_arguments(): # {{{1
    from optparse import OptionParser
    
    usage = """usage: %prog [options] folder1 folder2 ... folderN
    
    <<folder1>> to <<folderN>> should be folders containing benchmark 
    data for comparison. You should provide at least 2 folders."""   
    
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))
    parser.add_option("--build-folder", dest="build_folder", help="Name the folder all the result files should be places. This will include a Makefile, a number of data files, gnuplot files etc. If no argument is given the script will try to create a <result> folder in the current directory")
    parser.add_option("--exclude-makefile", dest="makefile", action="store_false", default=True)
    parser.add_option("--run-makefile", dest="makefile_executed", action="store_true", default=False)
    options, args = parser.parse_args()
    
    if len(args) <= 1:
        parser.error("You should provide at least two folders with benchmarks data for comparison.")

    # Test if we try to avoid the makefile but run make anyway.
    if (not options.makefile) and options.makefile_executed:
        parser.error("options --execlude-makefile and --run-makefile are mutually exclusive")
    
    return args, options
# }}}1

class SingleDataGather(object): # {{{1
    def __init__(self, folder_prefixes): # {{{2
        self.tags = set([])
        self.parsed_csv_files = 0
        self._find_csv_files(folder_prefixes)
        self._parse()
    # }}}2
    def _add_tag(self, tag): # {{{2
        self.tags.add(tag)
    # }}}2
    def get_tags(self): # {{{2
        tags = list(self.tags)
        tags.sort()
        return tags
# }}}2
    def _find_csv_files(self, folder_prefixes): # {{{2
        """
        This is the initial phase of the parsing. Using the folder prefixes we
        find all the potential single benchmark datafiles and put them in an
        internal structure for later parsing. 
        """
        self.csv_files = []
        for fp in folder_prefixes:
            self.csv_files.extend(glob.glob(fp+ "pupymark.sing.[0-9]*procs*"))
    # }}}2
    def _parse(self): # {{{2
        """
        Goes through the possile csv files and parse the contents into an
        internal format. 

        XXX: We could make a very simple argument here to dump the internal
        format to a pickles file so we can re-read it at a later point
        """
        data = {}
        
        # Regular match to find the tags
        tag_procs_re = re.compile(".*/benchmark_data/(?P<tag>\d+)-benchmark_output.*\.sing\.(?P<procs>\d+).*")

        for filename in self.csv_files:
            reader = csv.reader(open(filename))
            self.parsed_csv_files += 1
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
                run_type = row[6].replace("test_","")

                # The number of procs seems inconsistant. 
                procs = row[5]

                # Find the tags from the filename
                match = tag_procs_re.match(filename)

                # We override the <<procs>> here. Maybe we should not
                tag, procs = match.groups()
                self._add_tag(tag) 

                # Add the data to the internal structure
                if run_type not in data:
                    data[run_type] = {}

                if procs not in data[run_type]:
                    data[run_type][procs] = {}

                if tag not in data[run_type][procs]:
                    data[run_type][procs][tag] = []

                # Actual add the data point to the list
                data[run_type][procs][tag].append( (datasize, time_p_it) )

        self.data = data
    # }}}2
# }}}1
class Plotter(object): # {{{1
    def __init__(self, data_obj, output_folder=None):
        self.data = data_obj
        if output_folder:
            self.output_folder = output_folder
        else:
            self.output_folder = self._create_output_folder()

    def _create_output_folder(self):
        base_name = "plot_output"
        counter = 0

        while True:
            output_folder_name = base_name
            if counter > 0:
                output_folder_name += "%d" % counter

            try:
                os.mkdir(output_folder_name)
                return output_folder_name
            except OSError:
                counter += 1
# }}}1
class SinglePlotter(Plotter):
    pass

def draw_scatter(gather, folder): # {{{1
    """
    This function will output a lot of gnuplot data
    to be manualle executed. This gives you the option
    to make last minute (or second) changes in captions
    etc. Face it.. captions should be manually 
    written
    """
    
    def get_x_tics(data): # {{{2
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
    # }}}2 
    def get_y_tics(max_value): # {{{2
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
    # }}}2 
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
# }}}1
def write_gnuplot_makefile(folder_name): # {{{1
    fh = open(folder_name+"/Makefile", "w")
    
    print >> fh, "all:"
    print >> fh, "\tgnuplot *.gnu\n"
    print >> fh, "clean:"
    print >> fh, "\trm *.png"
    fh.close()            
# }}}1
if __name__ == "__main__":
    start_time = time.time()
    # Handle arguments etc. 
    folders, options = options_and_arguments()

    # Initialize a gather object. This object will hold all data
    # and make it possible to extract it later. 
    gather = SingleDataGather(folders)

    single_plotter = SinglePlotter(gather, output_folder=options.build_folder)
    output_folder = single_plotter.output_folder

    # Check if we should place a makefile in the final folder. 
    if options.makefile:
        write_gnuplot_makefile(output_folder)

    if options.makefile_executed:
        os.chdir(output_folder)
        subprocess.Popen(["make"])

    tags = ", ".join(gather.get_tags())

    total_time = time.time() - start_time

    
    # Print some informative text to the end user.
    print """
================================================================================ 
Comparison tags %s
================================================================================ 

    Compared tags          :      %s
    Output written to      :      %s
    Parsed csv files       :      %d
    Makefile written       :      %s
    Timing                 :      %.2f seconds
    Executed Makefile      :      %s
    
""" % (tags, tags, output_folder, gather.parsed_csv_files, options.makefile, total_time, options.makefile_executed)

if not options.makefile_executed:
    print """
No graphs generated yet. To generate it run the following:

    > cd %s
    > Make
""" % output_folder




    


   ## Ensure we have the output folder
   #output_folder_name = options.build_folder
   #import os
   #try:
   #    os.mkdir(output_folder_name)
   #except OSError:
   #    pass

   ## Were we should actually look if we're using gnuplot
   ## and only write the makefile if so.
   #write_gnuplot_makefile(output_folder_name)
   #
   ## If we should choose to implement further output functions we should
   ## add an options above and select an output function here.
   #def timer_wrapper():    
   #    draw_scatter(gather, output_folder_name)
   #
   ## Stop the timing and say goodbye.
   #from timeit import Timer
   #t = Timer(timer_wrapper)
   #t = t.timeit(number=1)
   #
   #print """
   #Goodbye. We parsed %d benchmark folders in %.2f seconds. 
   #
   #You can generate all the final files by changing into the %s folder 
   #and type "Make".
   #""" % (len(folders), t, output_folder_name)
