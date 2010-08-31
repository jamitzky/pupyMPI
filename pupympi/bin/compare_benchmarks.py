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
import os, sys, glob, csv, re, time, subprocess, copy

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
    parser.add_option("--aggregation-method", dest="agg_method", default="avg", help="Which aggregation method used to summarize the data items for equal x values. Defaults to 'avg', but other choices are 'sum', 'min' and 'max'. You can use a comma list like 'sum,avg'")
    options, args = parser.parse_args()
    
    if len(args) <= 1:
        parser.error("You should provide at least two folders with benchmarks data for comparison.")

    # Test if we try to avoid the makefile but run make anyway.
    if (not options.makefile) and options.makefile_executed:
        parser.error("options --execlude-makefile and --run-makefile are mutually exclusive")

    methods = options.agg_method.split(",")
    func_methods = []
    for method in methods:
        # Clean the aggregation method to a function
        if method == "sum":
            fmethod = sum
        elif method == "min":
            fmethod = min 
        elif method == "max":
            fmethod = max 
        elif method == "avg":
            fmethod = lambda x: sum(x)/float(len(x))

        func_methods.append((method, fmethod))
    options.agg_methods = func_methods

    return args, options
# }}}1
class SingleDataGather(object): # {{{1
    def __init__(self, folder_prefixes, agg_methods): # {{{2
        self.tags = set([])
        self.parsed_csv_files = 0
        self._find_csv_files(folder_prefixes)
        self._parse()
        self.aggregate(agg_methods)
    # }}}2
    def aggregate(self, methods):
        """
        This method runs through the data and aggregates data for equal 
        x values. 
        
        These data is then used to construct a number of line graphs. 
        """
        data = copy.deepcopy(self.data)

        for test in data:
            for procs in data[test]:
                for tag in data[test][procs]:
                    d = {}
                    for e in data[test][procs][tag]:
                        x, y = e
                        if x not in d:
                            d[x] = []
                        d[x].append(y)
                    data[test][procs][tag] = {}
                    # The dict d now contains a number of elements for each x value. We can how
                    # run through that dict constructing a tuple with (x, agg_f(y_values)) and
                    # use that. 
                    for x in d:
                        for ft in methods:
                            (fname, func) = ft
                            if fname not in data[test][procs][tag]:
                                data[test][procs][tag][fname] = []
                            data[test][procs][tag][fname].append((x, func(d[x])))
        self.agg_data = data
        
    def _add_tag(self, tag): # {{{2
        self.tags.add(tag)
    # }}}2
    def get_tags(self): # {{{2
        tags = list(self.tags)
        tags.sort()
        return tags
    # }}}2
    def get_tests(self): # {{{2
        return self.data.keys()
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
                data[run_type][procs][tag].append( (int(datasize), float(time_p_it)) )

        self.data = data
    # }}}2
    def get_data(self, test_name): # {{{2
        return self.data[test_name]
    # }}}2
# }}}1
class Plotter(object): # {{{1
    def __init__(self, data_obj, output_folder=None): # {{{2
        self.data = data_obj
        if output_folder:
            self.output_folder = output_folder
        else:
            self.output_folder = self._create_output_folder()
     # }}}2
    def _create_output_folder(self): # {{{2
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
    # }}}2
# }}}1
class GNUPlot(object): # {{{1
    def gnuplot_datasize_tics(self, data): # {{{2
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
    def gnuplot_time_tics(self, max_value): # {{{2
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
# }}}1
class ScatterPlot(GNUPlot): # {{{1
    def __init__(self, test_name=None, test_type="single", output_folder=None): # {{{2
        self.test_name = test_name
        self.test_type = test_type
        self.data = []
        self.output_folder = output_folder
        self.buffer_factor = 1.25
    # }}}2
    def add_data(self, procs, tag, plots): # {{{2
        self.data.append( (procs, tag, plots) )
    # }}}2
    def get_buffered_x_max(self): # {{{2
        return max(1, round(self.x_max*self.buffer_factor))
    # }}}2
    def get_buffered_y_max(self): # {{{2
        return max(1, round(self.y_max*self.buffer_factor))
    # }}}2
    def find_max_and_min(self): # {{{2
        x_data = []
        y_data = [] 

        for element in self.data:
            _, _, plots = element
            x_data.extend([p[0] for p in plots])
            y_data.extend([p[1] for p in plots])

        self.x_min = min(x_data)
        self.x_max = max(x_data)
        self.y_min = min(y_data)
        self.y_max = max(y_data)

        self.x_data = list( set( x_data))
        self.x_data.sort()
    # }}}2
    def plot(self): # {{{2
        self.find_max_and_min()
        
        # Basic data for all the files.
        filename = "scatter_%s" % self.test_name

        # Flush all the data files. 
        dat_files = []
        for element in self.data:
            procs, tag, plots = element
            dat_filename_file = "%s_%s_%s.dat" % (filename, procs, tag)
            dat_filename_path = self.output_folder + "/" + dat_filename_file
            dat_files.append( (procs, tag, dat_filename_file ) )
            dat_fp = open(dat_filename_path, "w")

            for e in plots:
                print >> dat_fp, "%d %f" % e

            dat_fp.close()

        # Write the .gnu file
        title = "Scatter plot for %s" % self.test_name
        gnu_fp = open(self.output_folder + "/" + filename + ".gnu", "w")

        print >> gnu_fp, "set terminal png nocrop enhanced size 800,600"
        print >> gnu_fp, 'set output "%s.png"' % filename
        print >> gnu_fp, 'set title "%s"' % title
        print >> gnu_fp, 'set xlabel "Data size"'
        print >> gnu_fp, 'set ylabel "Wallclock in'
        print >> gnu_fp, 'set xtic nomirror rotate by -45 scale 0 offset 0,-2 '
        print >> gnu_fp, 'set xtics (%s)' % ", ".join(self.gnuplot_datasize_tics(self.x_data))
        print >> gnu_fp, 'set ytics (%s)' % ", ".join(self.gnuplot_time_tics(self.y_max))
        print >> gnu_fp, "set log x"
        print >> gnu_fp, "set log y"

        # Setting x-range and y-range. 
        print >> gnu_fp, "set xrange [1:%d]" % self.get_buffered_x_max()
        print >> gnu_fp, "set yrange [1:%d]" % self.get_buffered_y_max()

        # Different line types. 
        print >> gnu_fp, 'set style line 1 linetype 1 linecolor rgb "red" linewidth 1.000 pointtype 1 pointsize default'
        print >> gnu_fp, 'set style line 2 linetype 2 linecolor rgb "orange" linewidth 1.000 pointtype 2 pointsize default'
        print >> gnu_fp, 'set style line 3 linetype 3 linecolor rgb "yellow" linewidth 1.000 pointtype 3 pointsize default'
        print >> gnu_fp, 'set style line 4 linetype 4 linecolor rgb "green" linewidth 1.000 pointtype 4 pointsize default'
        print >> gnu_fp, 'set style line 5 linetype 5 linecolor rgb "cyan" linewidth 1.000 pointtype 5 pointsize default'
        print >> gnu_fp, 'set style line 6 linetype 6 linecolor rgb "blue" linewidth 1.000 pointtype 6 pointsize default'
        print >> gnu_fp, 'set style line 7 linetype 7 linecolor rgb "violet" linewidth 1.000 pointtype 7 pointsize default'

        i = 0
        plot_str = 'plot '
        plot_strs = []
        for p in dat_files:
            i += 1
            (procs, tag, dat_filename) = p
            title = "%s procs (Tag: %s)" % (procs, ".".join(tag))
            plot_strs.append(' "%s" ls %d title "%s"' % (dat_filename, i, title))
            
        plot_str += ", ".join(plot_strs)
        print >> gnu_fp, plot_str

        gnu_fp.close()
    # }}}2
# }}}1
class SinglePlotter(Plotter): # {{{1
    def __init__(self, *args, **kwargs):
        super(SinglePlotter, self).__init__(*args, **kwargs)

        self.scatter_plot()

    def scatter_plot(self):
        for test in self.data.get_tests():
            sp = ScatterPlot(test_name=test, test_type="single", output_folder=self.output_folder)
            data = self.data.get_data(test)
            for procs in data:
                for tag in data[procs]:
                    sp.add_data(procs, tag, data[procs][tag])
            
            sp.plot()
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
    gather = SingleDataGather(folders, options.agg_methods)

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
    Aggregation methods    :      %d (%s)
    
""" % (".".join(tags), ".".join(tags), output_folder, gather.parsed_csv_files, options.makefile, total_time, options.makefile_executed, len(options.agg_methods), ", ".join([x[0] for x in options.agg_methods]))

if not options.makefile_executed:
    print """
No graphs generated yet. To generate it run the following:

    > cd %s
    > Make
""" % output_folder
