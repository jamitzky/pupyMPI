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
# imports {{{1
import os, sys, glob, csv, re, time, subprocess, copy, math

mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

from mpi import constants
# }}}1
def options_and_arguments(): # {{{1
    from optparse import OptionParser, OptionGroup
    
    usage = """usage: %prog [options] folder1 folder2 ... folderN
    
    <<folder1>> to <<folderN>> should be folders containing benchmark 
    data for comparison."""   
    
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))
    parser.add_option("--build-folder", dest="output_folder", help="The folder containing the GNUPlot files. If not given a folder called 'plot_output' will be created. If that folder already exists 'plot_output1', 'plot_output2'... will be created. ")
    parser.add_option("-q", "--quiet", dest="verbose", action="store_false", help="Silent mode. No final message etc")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=True, help="Verbose mode. The default choice. Disable with -q")

    timing_group = OptionGroup(parser, "Timing options", "Options for data handling, cleaning and aggregation. See description for each option below")
    timing_group.add_option("--aggregation-method", dest="agg_method", default="avg", help="Which aggregation method used to summarize the data items for equal x values. Defaults to 'avg', but other choices are 'sum', 'min' and 'max'. You can use a comma list like 'sum,avg'")
    timing_group.add_option("--value-method", dest="value_method", choices=['throughput','avg','min','max'], default="avg", help="Which measurement method should be used for the plots. Use min (or max) to select the fastest (or slowest) node in a given operation or average to get the avg between the nodes. Use 'throughput' to plot thoughput. Defaults to %default")
    timing_group.add_option("--speedup-baseline-tag", dest="speedup_baseline_tag", help="What tag to use as a baseline in the speedup. If not supplied or the given tag is invalid we use the lowest tag. Giving a invalid tag will issue a warning.")
    parser.add_option_group(timing_group)

    plot_group = OptionGroup(parser, "Plotting options", "Handling different sizes, axis scale etc. Changing settings here will change all the generated pictures. Changing a single picture can be done in a single .gnu file in the result folder")
    plot_group.add_option("--plot-height", type="int", default=600, dest="plot_height", help="The height of the generated images. Defaults to %default")
    plot_group.add_option("--plot-width", type="int", default=800, dest="plot_width", help="The width of the generated images. Defaults to %default")
    plot_group.add_option("--plot-x-axis-type", dest="x_axis_type", default="log", choices=['log','lin'], help="How the x axis should be scaled. Options: log or lin. Defaults to %default")
    plot_group.add_option("--plot-y-axis-type", dest="y_axis_type", default="log", choices=['log','lin'], help="How the y axis should be scaled. Options: log or lin. Defaults to %default")
    parser.add_option_group(plot_group)

    makefile_group = OptionGroup(parser, "Makefile options", "Options to disable the generation of a Makefile and an option to execute it if generated")
    makefile_group.add_option("--exclude-makefile", dest="makefile", action="store_false", default=True, help="Don't create a Makefile")
    makefile_group.add_option("--run-makefile", dest="makefile_executed", action="store_true", default=False, help="Execute the Makefile (which will generate the images)")
    parser.add_option_group(makefile_group)
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
        def avg(l):
            if len(l) == 0:
                return None
            else:
                return sum(l)/float(len(l))

        def _sum(l):
            if len(l) == 0:
                return None
            else:
                return sum(l)

        def _min(l):
            if len(l) == 0:
                return None
            else:
                return min(l)

        def _max(l):
            if len(l) == 0:
                return None
            else:
                return max(l)

        lookup = { "sum" : _sum, "min" : _min, "max" : _max, "avg" : avg }
        fmethod = lookup[method]
        func_methods.append((method, fmethod))

    options.agg_methods = func_methods

    return args, options
# }}}1
class DataGather(object): # {{{1
    def __init__(self, folder_prefixes, agg_methods, value_method="avg", speedup_baseline_tag=None): # {{{2
        self.tags = set([])
        self.parsed_csv_files = 0
        self._find_csv_files(folder_prefixes)
        self._parse(value_method=value_method)
        self.calculate_speedup(speedup_baseline_tag)
        self.aggregate(agg_methods)
    # }}}2
    def calculate_speedup(self, baseline_tag=None): # {{{2
        """
        Find the lowest tag and use that as a baseline if you don't give one
        through the command line options. 

        This only calculates the internal speedup, so the plotting afterwards
        can be both a scatterplot and lineplot. 
        """
        # If we have a tag, we validate that it actually exists. 
        if baseline_tag and baseline_tag not in self.tags:
            print "Warning. The supplied tag '%s' for speedup is not parsed" % baseline_tag
            baseline_tag = None

        if not baseline_tag:
            baseline_tag = min(self.tags)

        # The speed up is calculated by having populating a new data set in the same
        # structure as the original data. For each data list we sort the baseline
        # list and the other list. For <<baseline>> list and <<compare>> list we find
        # scale_i (scaling factor for item i) by dividing baseline_i with compare_i. We
        # also do this for the baseline itself (will just give a plain and nice 1).
        scale_data = {}
        for test_name in self.data:
            if test_name not in scale_data:
                scale_data[test_name] = {}

            for procs in self.data[test_name]:
                if procs not in scale_data[test_name]:
                    scale_data[test_name][procs] = {}

                for tag in self.data[test_name][procs]:
                    baseline = self.data[test_name][procs][baseline_tag]
                    tocompare = self.data[test_name][procs][tag]

                    # We sort the lists so we don't get strange items comapred
                    baseline.sort()
                    tocompare.sort()

                    # Create the new item
                    l = []
                    for i in range(len(baseline)):
                        t = tocompare[i][1]
                        b = baseline[i][1]

                        if tocompare[i][0] != baseline[i][0]:
                            print "Warning. We compare unequal data sizes"

                        # FIXME: We might want to insert some crap value like 0 or 1
                        try:
                            scale = b / t
                        except ZeroDivisionError:
                            scale = None

                        l.append( (baseline[i][0], scale))

                    scale_data[test_name][procs][tag] = l
        self.scale_data = scale_data
    # }}}2
    def aggregate(self, methods): # {{{2
        """
        This method runs through the data and aggregates data for equal 
        x values. 
        
        These data is then used to construct a number of line graphs. 
        """
        for item in ("data", "scale_data"): 
            data = getattr(self, item)
            agg_data = {}
            for test in data:
                if test not in agg_data:
                    agg_data[test] = {}

                for procs in data[test]:
                    if procs not in agg_data[test]:
                        agg_data[test][procs] = {}

                    for tag in data[test][procs]:
                        if tag not in agg_data[test][procs]:
                            agg_data[test][procs][tag] = {}

                        d = {}
                        for e in data[test][procs][tag]:
                            x, y = e
                            if x not in d:
                                d[x] = []
                            d[x].append(y)
                        # The dict d now contains a number of elements for each x value. We can how
                        # run through that dict constructing a tuple with (x, agg_f(y_values)) and
                        # use that. 
                        for x in d:
                            for ft in methods:
                                (fname, func) = ft
                                if fname not in agg_data[test][procs][tag]:
                                    agg_data[test][procs][tag][fname] = []
                                values = filter(lambda x: x is not None, d[x])
                                agg_data[test][procs][tag][fname].append((x, func(values)))
            setattr(self, "agg_"+item, agg_data)
    # }}}2
    def _add_tag(self, tag): # {{{2
        self.tags.add(tag)
    # }}}2
    def get_tags(self): # {{{2
        tags = list(self.tags)
        tags.sort()
        return tags
    # }}}2
    def _filter(self, org_keys, exclude): # {{{2
        keys = []
        for key in org_keys:
            comp_key = key.lower() 
            found = False
            for ex in exclude:
                if comp_key.find(ex) > -1:
                    found = True
                    break
            if not found:
                keys.append(key)
        return keys
    # }}}2
    def get_tests(self, exclude=["barrier"]): # {{{2
        return self._filter(self.data.keys(), exclude)
    # }}}2
    def get_agg_tests(self, exclude=["barrier"]): # {{{2
        return self._filter(self.agg_data.keys(), exclude)
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
            self.csv_files.extend(glob.glob(fp+ "pupymark.coll.[0-9]*procs*"))
    # }}}2
    def _parse(self, value_method="avg"): # {{{2
        """
        Goes through the possile csv files and parse the contents into an
        internal format. 

        XXX: We could make a very simple argument here to dump the internal
        format to a pickles file so we can re-read it at a later point
        """
        data = {}
        
        # Regular match to find the tags
        tag_procs_re = re.compile(".*/benchmark_data/(?P<tag>\d+)-benchmark_output.*\.(sing|coll)\.(?P<procs>\d+).*")

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
                if len(row) == 10:
                    # new format
                    time_min = float(row[4])
                    time_max = float(row[5])
                    throughput = float(row[6])
                    run_type = row[8].replace("test_","")

                    # The number of procs seems inconsistant. 
                    procs = row[7]
                elif len(row) == 8:
                    # old format. Wasting memory due to lack of coding stills by CB
                    time_min = float(time_p_it)
                    time_max = float(time_p_it)

                    throughput = float(row[4])
                    run_type = row[6].replace("test_","")

                    # The number of procs seems inconsistant. 
                    procs = row[5]
                else:
                    print "WARNING: Found a row with a strange number of rows:", len(row)

                # It appers that throughput is in MB/s. The internal use is in B/sec, so we convert it
                throughput = throughput * 1024**2

                # Find the tags from the filename
                match = tag_procs_re.match(filename)

                # We override the <<procs>> here. Maybe we should not
                tag, _,procs = match.groups()
                self._add_tag(tag) 

                # Add the data to the internal structure
                if run_type not in data:
                    data[run_type] = {}

                if procs not in data[run_type]:
                    data[run_type][procs] = {}

                if tag not in data[run_type][procs]:
                    data[run_type][procs][tag] = []

                # Select which timing data to use
                item = time_p_it
                if value_method == "min":
                    item = time_min
                elif value_method == "max":
                    item = time_max
                elif value_method == "throughput":
                    item = throughput

                # Actual add the data point to the list
                data[run_type][procs][tag].append( (int(datasize), float(item)) )

        self.data = data
    # }}}2
# }}}1
class Plotter(object): # {{{1
    def __init__(self, data_obj, settings, **kwargs): # {{{2
        self.data = data_obj
        self.settings = settings
        if settings.output_folder:
            self.output_folder = settings.output_folder
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
    def format_size(self, bytecount):
        n = math.log(size, 2)
        border_list = [ (10, "B"), (20, "KB"), (30, "MB"), (40, "GB"), (50, "TB") ]
        for bl in border_list:
            if n < bl[0]:
                return "%.2f %s" % (float(size) / 2**(bl[0]-10), bl[1])
        return "%.2f B" % size

    def format_traffic(self, bytecount):
        return format_size(bytecount)+"/s"
        
    def format_scale(self, scale):
        return "%.2f" % scale

    def format_time(self, usecs):
        pass

    def format_labels(self, axis_max=2, axis_size=600, pixels_per_label=10, format_type="size"):
        """
        Find the labels on an axis (x or y) by calculating the maximum distance
        between labels and another things. We know the size of the plot, so we
        can calculate how many labels fit. 

        The steps for finding the proper GNUPlot labels:

           1) Create a general list with potential labels for latering
              filtering.
           2) Calculate the number of labels that will fit into the plot.
           3) Fit the number of labels to the potential labels.
           4) Go through the list and format each element. We'll call a simple
              formatting function on each element. The function depends on
              the axis type.
        """
        # 1) 
        initial_range = range(1, axis_max, 10)

        # 2) Calculate the number of labels. We subtract 40 pixels from the given
        #    size because gnuplot needs some splace to captions / labels etc.
        axis_size -= 40.0
        labels = axix_size / pixels_per_label

        # Adjust the labels by finding the <<skip>> factor to filter the
        # potential list. If - for example - we have 1000 potential labels but
        # room for 20 we should include the 1000/20'th label.
        skip_factor = math.ceil(len(axis_max) / labels)

        raw_labels = adjusted_range[::skip_factor] # OK. This is smart

        # 4) Format the data. 
        formatter = { 'size' : self.format_size, 'time' : self.format_time, 'scale' : self.format_scale }[format_type]
        formatted_labels = [ (x, formatter(x)) for x in raw_labels]

        return formatted_labels

       #if self.y_type == "time":
       #    y_tics = self.gnuplot_time_tics(self.y_max)
       #else:
       #    y_tics = self.gnuplot_traffic_tics(self.y_max)

       #print >> gnu_fp, 'set ytics (%s)' % ", ".join(y_tics)
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
    def set_height(self, height): # {{{2
        self.plot_height = height
    # }}}2
    def set_width(self, width): # {{{2
        self.plot_width = width
    # }}}2
    def set_prefix(self, prefix): # {{{2
        self.prefix = prefix
    # }}}2
    def set_axis_type(self, x_axis_type, y_axis_type): # {{{2
        self.y_axis_type = y_axis_type
        self.x_axis_type = x_axis_type
    # }}}2
    def set_y_type(self, y_type): # {{{2
        self.y_type = y_type
        lookup = { 'time' : "Wallclock", 'scale' : "Speedup", 'throughput' : "Throughput" }
        self.y_label = lookup[y_type]
    # }}}2
# }}}1
class LinePlot(GNUPlot): # {{{1
    def __init__(self, title_help=None, test_name=None, test_type="single", output_folder=None): # {{{2
        self.test_name = test_name
        self.test_type = test_type
        self.title_help = title_help
        self.data = []
        self.output_folder = output_folder
    # }}}2
    def add_data(self, procs, tag, plots): # {{{2
        self.data.append( (procs, tag, plots) )
    # }}}2
    def plot(self): # {{{2
        self.find_max_and_min()
        # Basic data for all the files.
        filename = "%s_line_%s_%s" % (self.prefix, self.title_help, self.test_name)

        # Flush all the data files. 
        dat_files = []
        for element in self.data:
            procs, tag, plots = element
            dat_filename_file = "%s_%s_%s.dat" % (filename, procs, tag)
            dat_filename_path = self.output_folder + "/" + dat_filename_file
            dat_files.append( (procs, tag, dat_filename_file ) )
            dat_fp = open(dat_filename_path, "w")

            plots.sort(key=lambda x: x[0])

            for e in plots:
                if e[1] is not None:
                    print >> dat_fp, "%d %f" % e

            dat_fp.close()

        # Write the .gnu file
        title = "Plot for %s" % self.test_name
        gnu_fp = open(self.output_folder + "/" + filename + ".gnu", "w")

        print >> gnu_fp, "set terminal png nocrop enhanced size %d,%d" % (self.plot_width, self.plot_height)
        print >> gnu_fp, 'set output "%s.png"' % filename
        print >> gnu_fp, 'set title "%s"' % title
        print >> gnu_fp, 'set xlabel "Data size"'
        print >> gnu_fp, 'set ylabel "%s"' % self.y_label
        print >> gnu_fp, 'set xtic nomirror rotate by -45 scale 0 offset 0,-2 '
        print >> gnu_fp, 'set xtics (%s)' % ", ".join(self.gnuplot_datasize_tics(self.x_data))

        self._print_and_format(gnu_fp, axis_max=self.y_max)

        if self.y_axis_type == "log":
            print >> gnu_fp, "set log y"

        if self.x_axis_type == "log":
            print >> gnu_fp, "set log x"

        plot_str = 'plot '
        plot_strs = []
        for p in dat_files:
            (procs, tag, dat_filename) = p
            title = "%s procs (Tag: %s)" % (procs, ".".join(tag))
            plot_strs.append(' "%s" with linespoints title "%s"' % (dat_filename, title))
            
        plot_str += ", ".join(plot_strs)
        print >> gnu_fp, plot_str

        gnu_fp.close()
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
    def plot(self): # {{{2
        self.find_max_and_min()
        
        # Basic data for all the files.
        filename = "%s_scatter_%s" % (self.prefix, self.test_name)

        # Flush all the data files. 
        dat_files = []
        for element in self.data:
            procs, tag, plots = element
            dat_filename_file = "%s_%s_%s.dat" % (filename, procs, tag)
            dat_filename_path = self.output_folder + "/" + dat_filename_file
            dat_files.append( (procs, tag, dat_filename_file ) )
            dat_fp = open(dat_filename_path, "w")

            for e in plots:
                if e[1] is not None:
                    print >> dat_fp, "%d %f" % e

            dat_fp.close()

        # Write the .gnu file
        title = "Plot for %s" % self.test_name
        gnu_fp = open(self.output_folder + "/" + filename + ".gnu", "w")

        print >> gnu_fp, "set terminal png nocrop enhanced size %d,%d" % (self.plot_width, self.plot_height)
        print >> gnu_fp, 'set output "%s.png"' % filename
        print >> gnu_fp, 'set title "%s"' % title
        print >> gnu_fp, 'set xlabel "Data size"'
        print >> gnu_fp, 'set ylabel "%s"' % self.y_label
        print >> gnu_fp, 'set xtic nomirror rotate by -45 scale 0 offset 0,-2 '
        print >> gnu_fp, 'set xtics (%s)' % ", ".join(self.gnuplot_datasize_tics(self.x_data))

        self._print_and_format(gnu_fp, axis_max=self.y_max)

        if self.y_axis_type == "log":
            print >> gnu_fp, "set log y"

        if self.x_axis_type == "log":
            print >> gnu_fp, "set log x"

        # Setting x-range and y-range. 
        print >> gnu_fp, "set xrange [1:%d]" % max(2,self.get_buffered_x_max())
        print >> gnu_fp, "set yrange [1:%d]" % max(2, self.get_buffered_y_max())

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
    def __init__(self, *args, **kwargs): # {{{2
        super(SinglePlotter, self).__init__(*args, **kwargs)
        y_type = "time"
        if self.settings.value_method == "throughput":
            y_type = "traffic"
        self.y_type = y_type
        self.agg_methods = self.settings.agg_methods
        self.scatter_plot()
        self.line_plot()
    # }}}2
    def line_plot(self): # {{{2
        """
        Use the aggregated data for a number of line plots
        """
        # Run through the normal data and the scale data
        for run_type in [ ("normal", "data"), ("scale", "scale_data") ]:
            for test in self.data.get_agg_tests():
                for agg_e in self.agg_methods:
                    agg_name, agg_func = agg_e

                    lp = LinePlot(test_name=test, title_help=agg_name, test_type="single", output_folder=self.output_folder)
                    lp.set_prefix( run_type[0] )
                    lp.set_height(self.settings.plot_height)
                    lp.set_width(self.settings.plot_width)
            
                    if run_type[0] == "scale":
                        lp.set_y_type("scale")
                    else:
                        lp.set_y_type(self.y_type)

                    lp.set_axis_type(self.settings.x_axis_type, self.settings.y_axis_type)
                    data = getattr(self.data, "agg_"+run_type[1])[test]
                    for procs in data:
                        for tag in data[procs]:
                            lp.add_data(procs, tag, data[procs][tag][agg_name])
                    lp.plot()
    # }}}2
    def scatter_plot(self): # {{{2
        """
        Use all the parsed data on a scatter plot. Each (tag, procs) pair will have a different
        color and labe, so it's possible to see the development.

        HINT: If you want data for only 32 procs on the chart, simply copy the genereated .gnu
        files and remove what you don't want plotted. 
        """
        for run_type in [ ("normal", "data"), ("scale", "scale_data") ]:
            for test in self.data.get_tests():
                sp = ScatterPlot(test_name=test, test_type="single", output_folder=self.output_folder)
                sp.set_prefix( run_type[0] )
                sp.set_height(self.settings.plot_height)
                sp.set_width(self.settings.plot_width)

                if run_type[0] == "scale":
                    sp.set_y_type("scale")
                else:
                    sp.set_y_type(self.y_type)

                sp.set_axis_type(self.settings.x_axis_type, self.settings.y_axis_type)
                data = getattr(self.data, run_type[1])[test]
                for procs in data:
                    for tag in data[procs]:
                        sp.add_data(procs, tag, data[procs][tag])
                
                sp.plot()
    # }}}2
# }}}1
def write_gnuplot_makefile(folder_name): # {{{1
    fh = open(folder_name+"/Makefile", "w")
    
    print >> fh, "all:"
    print >> fh, "\tgnuplot *.gnu\n"
    print >> fh, "clean:"
    print >> fh, "\trm *.png"
    fh.close()            
# }}}1
# MAIN EXECUTING CODE {{{1
if __name__ == "__main__":
    start_time = time.time()
    # Handle arguments etc. 
    folders, options = options_and_arguments()

    # Initialize a gather object. This object will hold all data
    # and make it possible to extract it later. 
    gather = DataGather(folders, options.agg_methods, options.value_method, options.speedup_baseline_tag)

    single_plotter = SinglePlotter(gather, options)
    output_folder = single_plotter.output_folder

    # Check if we should place a makefile in the final folder. 
    if options.makefile:
        write_gnuplot_makefile(output_folder)

    if options.makefile_executed:
        os.chdir(output_folder)
        subprocess.Popen(["make"])

    total_time = time.time() - start_time

    # Formatting the tags proper
    formatted_tags = []
    for tag in gather.get_tags():
        formatted_tags.append( ".".join(tag) )

    # Print some informative text to the end user.
    if options.verbose:
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
        
    """ % (", ".join(formatted_tags), ", ".join(formatted_tags), output_folder, gather.parsed_csv_files, options.makefile, total_time, options.makefile_executed, len(options.agg_methods), ", ".join([x[0] for x in options.agg_methods]))

    if options.verbose:
        if not options.makefile_executed:
            print """
        No graphs generated yet. To generate it run the following:

            > cd %s
            > Make
        """ % output_folder
# }}}1
