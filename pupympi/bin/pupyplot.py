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
def avg(l):
    if len(l) == 0:
        return None
    else:
        return sum(l)/float(len(l))

def get_font_path():
    import sys

    if sys.platform.find("linux") != -1:
        return '/usr/share/texmf-texlive/fonts/type1/urw/palatino/uplr8a.pfb'
    else:
        return '/usr/local/texlive/2009/texmf-dist/fonts/type1/urw/palatino/uplr8a.pfb'

def format_tag(tag):
    try:
        int(tag)
        return ".".join(tag)
    except:
        return tag.replace("_","-")

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
    plot_group.add_option("--plot-height", type="int", default=6, dest="plot_height", help="The height of the generated images. Defaults to %default")
    plot_group.add_option("--plot-width", type="int", default=8, dest="plot_width", help="The width of the generated images. Defaults to %default")
    plot_group.add_option("--plot-x-axis-type", dest="x_axis_type", default="log", choices=['log','lin'], help="How the x axis should be scaled. Options: log or lin. Defaults to %default")
    plot_group.add_option("--plot-y-axis-type", dest="y_axis_type", default="log", choices=['log','lin'], help="How the y axis should be scaled. Options: log or lin. Defaults to %default")
    plot_group.add_option("--plot-extra", dest="plot_extra", help="Link to a file that contains extra gnuplot commands. These will be inserted before the plot call")
    plot_group.add_option("--show-errors", dest="show_errors", action="store_true", default=False, help="Show error bars on the line plot. Only works in for the 'avg' aggregation method")
    parser.add_option_group(plot_group)

    makefile_group = OptionGroup(parser, "Makefile options", "Options to disable the generation of a Makefile and an option to execute it if generated")
    makefile_group.add_option("--exclude-makefile", dest="makefile", action="store_false", default=True, help="Don't create a Makefile")
    makefile_group.add_option("--run-makefile", dest="makefile_executed", action="store_true", default=False, help="Execute the Makefile (which will generate the images)")
    parser.add_option_group(makefile_group)
    options, args = parser.parse_args()

    # Test if we try to avoid the makefile but run make anyway.
    if (not options.makefile) and options.makefile_executed:
        parser.error("options --execlude-makefile and --run-makefile are mutually exclusive")

    methods = options.agg_method.split(",")
    func_methods = []
    for method in methods:
        # Clean the aggregation method to a function {{{2

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
        # }}}2
        lookup = { "sum" : _sum, "min" : _min, "max" : _max, "avg" : avg }
        fmethod = lookup[method]
        func_methods.append((method, fmethod))

    options.agg_methods = func_methods

    return args, options
# }}}1
def std_dev(dataset): # {{{1
    import math
    if not dataset or len(dataset) == 1:
        return None

    n = len(dataset)
    avg = float(sum(dataset))/n
    s = 0.0
    for data in dataset:
        diff = data - avg
        s += diff**2
    return math.sqrt((1/(float(n)-1))*s)
# }}}1
class DataGather(object): # {{{1
    def __init__(self, folder_prefixes, agg_methods, value_method="avg", speedup_baseline_tag=None): # {{{2
        lower_is_better = True
        if value_method == "throughput":
            lower_is_better = False

        self.tags = set([])
        self.parsed_csv_files = 0
        self._find_csv_files(folder_prefixes)
        self._parse(value_method=value_method)
        self.aggregate(agg_methods)
        self.calculate_point_speedup(speedup_baseline_tag)
        self.calculate_aggregate_speedup(speedup_baseline_tag, lower_is_better=lower_is_better)
    # }}}2
    def align_data(self, list1, list2, return_structs=False): # {{{2
        def struct(datalist):
            s = {}
            for element in datalist:
                (x, y) = element
                if x not in s:
                    s[x] = []
                s[x].append(element)
            return s

        struct1 = struct(list1)
        struct2 = struct(list2)

        if return_structs:
            return struct1, struct2

        # Find all the keys
        keys = struct1.keys()
        keys.extend(struct2.keys())

        # New elements
        new_list1 = []
        new_list2 = []

        # Create a new dict where each element
        # is the lowest amount of keys in the counts
        lengths = {}
        for key in keys:
            c1 = struct1.get(key, [])
            c2 = struct2.get(key, [])

            # Find the number of elements the two
            # list have in common.
            count = min(len(c1), len(c2))

            # Take the first <<count>> of each list
            # and append them to the final lists
            new_list1.extend( c1[:count] )
            new_list2.extend( c2[:count] )
        return new_list1, new_list2
    # }}}2
    def calculate_aggregate_speedup(self, baseline_tag=None, lower_is_better=True): # {{{2
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
                    if tag not in scale_data[test_name][procs]:
                        scale_data[test_name][procs][tag] = {'avg' : []}

                    try:
                        baseline = self.data[test_name][procs][baseline_tag]
                        tocompare = self.data[test_name][procs][tag]
                    except KeyError:
                        continue

                    baseline, tocompare = self.align_data(baseline, tocompare, return_structs=True)

                    # Get all the keys from the two
                    keys = baseline.keys()
                    keys.extend (tocompare.keys())
                    keys = list(set(keys))

                    for key in keys:
                        # avg baseline
                        try:
                            baseline_avg = avg( [x[1] for x in baseline[key] ])
                            tocompare_avg = avg( [x[1] for x in tocompare[key] ])
                        except KeyError:
                            continue

                        try:
                            if lower_is_better:
                                speedup = float(baseline_avg) / float(tocompare_avg)
                            else:
                                speedup = float(tocompare_avg) / float(baseline_avg)
                        except:
                            speedup = None

                        scale_data[test_name][procs][tag]['avg'].append( (key,speedup))

        self.agg_scale_data = scale_data
    # }}}2
    def calculate_point_speedup(self, baseline_tag=None): # {{{2
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
        data = copy.deepcopy(self.data)
        for test_name in data:
            if test_name not in scale_data:
                scale_data[test_name] = {}

            for procs in data[test_name]:
                if procs not in scale_data[test_name]:
                    scale_data[test_name][procs] = {}

                for tag in data[test_name][procs]:
                    try:
                        baseline = data[test_name][procs][baseline_tag]
                        tocompare = data[test_name][procs][tag]
                    except KeyError:
                        continue

                    # internal compare method {{{3
                    # We sort the lists so we don't get strange items comapred. We need a
                    # custom compare function as we need to sort the tuple by the first
                    # item, THEN by the second.
                    def compare(t1, t2): #
                        if t1[0] < t2[0]:
                            return -1
                        elif t1[0] > t2[0]:
                            return 1
                        else:
                            if t1[1] < t2[1]:
                                return -1
                            elif t1[1] > t2[1]:
                                return 1
                            else:
                                return 0
                    # }}}3

                    baseline = sorted(baseline, compare)
                    tocompare = sorted(tocompare, compare)

                    baseline, tocompare = self.align_data(baseline, tocompare)

                    if len(baseline) != len(tocompare):
                        print "WARNING: The length of <<baseline> and <<tocompare>> differs. We have an internal function to clean this"

                    # Create the new item
                    l = []
                    for i in range(len(baseline)):
                        t = tocompare[i][1]
                        b = baseline[i][1]

                        if tocompare[i][0] != baseline[i][0]:
                            print "Warning. We compare unequal data sizes", tocompare[i][0], baseline[i][0]

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
        data = copy.deepcopy(self.data)
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
                            agg_data[test][procs][tag][fname].append((x, func(values), std_dev(values)))
            self.agg_data = agg_data
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
            self.csv_files.extend(glob.glob(fp+ "pupymark.para.[0-9]*procs*"))
            self.csv_files.extend(glob.glob(fp+ "pupymark.sor.[0-9]*procs*"))
            self.csv_files.extend(glob.glob(fp+ "pupymark.accept.[0-9]*procs*"))
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
        tag_procs_re = re.compile("(.*/)?(?P<tag>\w+)-benchmark_output.*\.(sing|coll|para|sor|accept)\.(?P<procs>\d+).*")

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
                throughput = 0
                run_type = ""
                if len(row) == 10:
                    # new format
                    time_min = float(row[4])
                    time_max = float(row[5])
                    try:
                        throughput = float(row[6])
                    except:
                        throughput = 0

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
                elif len(row) == 7:
                    throughput = float(row[4])
                    run_type = row[5].replace("test_","")

                else:
                    print "WARNING: Found a row with a strange number of rows:", len(row)
                    print "\t", ",".join(row)

                # It appers that throughput is in MB/s. The internal use is in B/sec, so we convert it
                throughput = throughput * 1024**2

                # Find the tags from the filename
                match = tag_procs_re.match(filename)
                continue
                if not match:
                    print "Found problem with filename", filename

                # We override the <<procs>> here. Maybe we should not
                _, tag, _,procs = match.groups()

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
    def sort_data(self):
        def compare(t1, t2):
            if int(t1[0]) < int(t2[0]):
                return -1
            elif int(t1[0]) > int(t2[0]):
                return 1
            else:
                if t1[1] < t2[1]:
                    return -1
                elif t1[1] > t2[1]:
                    return 1
                else:
                    return 0

        self.data = sorted(self.data, compare)
    def write_extra(self, gnu_fp, filename): # {{{2
        if filename:
            fp = open(filename, "r")
            for line in fp:
                print >> gnu_fp, line.strip().strip()
    # }}}2
    def get_buffered_x_max(self, format_type="time"): # {{{2
        m = max(1, round(self.x_max*self.buffer_factor))
        if format_type == "scale":
            m = max(m, 2)
        return m
    # }}}2
    def get_buffered_y_max(self, format_type="time"): # {{{2
        m = max(1, round(self.y_max*self.buffer_factor))
        if format_type == "scale":
            m = max(m, 2)
        return m
    # }}}2
    def format_size(self, bytecount, decimals=0): # {{{2
        if bytecount == 0:
            return "0 B"
        n = math.log(bytecount, 2)
        border_list = [ (10, "B"), (20, "KB"), (30, "MB"), (40, "GB"), (50, "TB") ]
        fmt_str = "%%.%df%%s" % decimals
        for bl in border_list:
            if n < bl[0]:
                return fmt_str % (float(bytecount) / 2**(bl[0]-10), bl[1])
        return fmt_str % (bytecount, "B")
    # }}}2
    def format_traffic(self, bytecount): # {{{2
        return self.format_size(bytecount, decimals=1)+"/s"
    # }}}2
    def format_scale(self, scale): # {{{2
        return "%.0f" % scale
    # }}}2
    def format_time(self, usecs): # {{{2
        border_list = [ (1000, 'us'), (1000000, 'ms'), (1000000000, 's'),]
        for i in range(len(border_list)):
            bl = border_list[i]
            if usecs < bl[0]:
                if i > 0:
                    usecs = usecs / border_list[i-1][0]
                return "%.0f%s" % (usecs, bl[1])
    # }}}2
    def get_initial_range(self, axis_max, format_type, scale_type):
        """
        This method returns a candidate axis range. The format type
        is used to find proper values. This is not pretty at all, but
        it works
        """
        labels = 20
        lowest_value = 0
        if scale_type == "log":
            lowest_value = 1

        if format_type == "scale":
            skip = int(math.ceil( axis_max / labels))
            r = range(lowest_value, max( int(math.ceil(axis_max)), lowest_value+2), skip)
            if axis_max not in r:
                r.append(axis_max)
            return r
        elif format_type == "time":
            result = []
            value = lowest_value
            if scale_type == "log":
                while value < axis_max:
                    result.append( value )
                    value *= 10
            else:
                skip = int(math.ceil( axis_max / labels))
                skip = skip - skip % 10 + 10
                while value < axis_max:
                    result.append(value)
                    value += skip
            return result
        elif format_type == "traffic":
            result = []
            value = lowest_value
            if scale_type == "log":
                while value < axis_max:
                    result.append( value )
                    value *= 2
            else:
                labels = 20
                skip = int(math.ceil( axis_max / labels))
                skip_base = math.ceil(math.log(skip, 2))
                skip = 2**skip_base
                while value < axis_max:
                    result.append(value)
                    value += skip
            return result
        else:
            print "Unhandled formatting type", format_type
            return range(lowest_value, int(math.ceil(axis_max)), 100)

    def format_tics(self, axis_data=None, axis_max=10, axis_size=600, pixels_per_label=20, format_type="size", scale_type="log"): # {{{2
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
        if not axis_data:
            # Find the lowest element. This is 0 unless we have a log scale,
            # in case we use 1 (otherwise we'll get a math domain error)
            raw_labels = self.get_initial_range(axis_max, format_type, scale_type)
        else:
            raw_labels = axis_data

        # 4) Format the data.
        formatter = { 'size' : self.format_size, 'time' : self.format_time, 'scale' : self.format_scale, 'traffic' : self.format_traffic }[format_type]
        used_strs = []
        formatted_labels = []
        for label in raw_labels:
            fmt = formatter(label)
            if fmt in used_strs:
                continue

            used_strs.append(fmt)
            formatted_labels.append("'%s' %d" % (formatter(label), label))

        return formatted_labels
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
        lookup = { 'time' : "Wallclock", 'scale' : "Speedup", 'traffic' : "Throughput" }
        self.y_label = lookup[y_type]
    # }}}2
# }}}1
class LinePlot(GNUPlot): # {{{1
    def __init__(self, title_help=None, test_name=None, test_type="single", output_folder=None, extra=None, show_errors=False): # {{{2
        self.buffer_factor = 1.25
        self.test_name = test_name
        self.test_type = test_type
        self.title_help = title_help
        self.data = []
        self.output_folder = output_folder
        self.extra = extra
        self.show_errors = show_errors
    # }}}2
    def add_data(self, procs, tag, plots): # {{{2
        self.data.append( (procs, tag, plots) )
    # }}}2
    def plot(self): # {{{2
        if not self.data:
            return

        try:
            self.find_max_and_min()
        except ValueError:
            print "Cant find max and min, so there is probably no data"
            return

        # Basic data for all the files.
        filename = "%s_line_%s_%s" % (self.prefix, self.title_help, self.test_name)

        # Flush all the data files.
        dat_files = []

        self.sort_data()

        for element in self.data:
            # only create files for non-empty plots
            procs, tag, plots = element
            if len(plots) > 0:
                dat_filename_file = "%s_%s_%s.dat" % (filename, procs, tag)
                dat_filename_path = self.output_folder + "/" + dat_filename_file
                dat_files.append( (procs, tag, dat_filename_file ) )
                dat_fp = open(dat_filename_path, "w")

                plots.sort(key=lambda x: x[0])

                for e in plots:
                    if e[1] is not None:
                        if self.show_errors:
                            err = 0
                            try:
                                err = e[2]
                            except IndexError:
                                pass

                            print >> dat_fp, "%d %f %f" % (e[0], e[1], err)
                        else:
                            print >> dat_fp, "%d %f" % (e[0], e[1])

                dat_fp.close()

        # Write the .gnu file
        title = "Plot for %s" % self.test_name
        gnu_fp = open(self.output_folder + "/" + filename + ".gnu", "w")

        print >> gnu_fp, "set term postscript eps enhanced color font 'Palatino' fontfile '%s' 24 size %d,%d" % (get_font_path(), self.plot_width, self.plot_height)

        print >> gnu_fp, 'set output "%s.eps"' % filename
        print >> gnu_fp, 'set title "%s"' % title
        print >> gnu_fp, 'set xlabel "Data size"'
        print >> gnu_fp, 'set ylabel "%s"' % self.y_label
        print >> gnu_fp, 'set xtic nomirror rotate by -45'
        print >> gnu_fp, 'set key top left'
        print >> gnu_fp, 'set tics out'
        self.write_extra(gnu_fp, self.extra)


        print >> gnu_fp, 'set xtics (%s)' % ", ".join(self.format_tics(axis_data=self.x_data, axis_size=self.plot_width, format_type="size"))
        print >> gnu_fp, 'set ytics (%s)' % ", ".join(self.format_tics(axis_max=self.y_max, format_type=self.y_type, scale_type=self.y_axis_type))

        y_min = 0
        if self.y_axis_type == "log":
            print >> gnu_fp, "set log y"
            y_min = 1

        x_min = 0
        if self.x_axis_type == "log":
            print >> gnu_fp, "set log x"
            x_min = 1

        # Setting x-range and y-range.
        print >> gnu_fp, "set xrange [%d:%d]" % (x_min, max(2,self.get_buffered_x_max(format_type=self.y_type)))
        print >> gnu_fp, "set yrange [%d:%d]" % (y_min, max(2, self.get_buffered_y_max(format_type=self.y_type)))

        plot_str = 'plot '
        plot_strs = []
        for p in dat_files:
            (procs, tag, dat_filename) = p
            errorbar = ""
            if self.show_errors:
                title = "std. var. error for %s procs (Tag: %s)" % (procs, format_tag(tag))
                plot_strs.append(' "%s" with yerrorbars title "%s" %s' % (dat_filename, title, errorbar))

            title = "%s procs (Tag: %s)" % (procs, format_tag(tag))
            plot_strs.append(' "%s" with linespoints title "%s" %s' % (dat_filename, title, errorbar))

        plot_str += ", ".join(plot_strs)
        print >> gnu_fp, plot_str

        gnu_fp.close()
    # }}}2
# }}}1
class ScatterPlot(GNUPlot): # {{{1
    def __init__(self, test_name=None, test_type="single", output_folder=None, extra=None): # {{{2
        self.test_name = test_name
        self.test_type = test_type
        self.data = []
        self.output_folder = output_folder
        self.buffer_factor = 1.25
        self.extra = extra
    # }}}2
    def add_data(self, procs, tag, plots): # {{{2
        self.data.append( (procs, tag, plots) )
    # }}}2
    def plot(self): # {{{2
        if not self.data:
            return

        self.find_max_and_min()

        # Basic data for all the files.
        filename = "%s_scatter_%s" % (self.prefix, self.test_name)

        self.sort_data()

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

        print >> gnu_fp, "set term postscript eps enhanced color font 'Palatino' fontfile '%s' 24 size %d,%d" % (get_font_file(), self.plot_width, self.plot_height)
        print >> gnu_fp, 'set output "%s.eps"' % filename
        print >> gnu_fp, 'set title "%s"' % title
        print >> gnu_fp, 'set xlabel "Data size"'
        print >> gnu_fp, 'set ylabel "%s"' % self.y_label
        print >> gnu_fp, 'set xtic nomirror rotate by -45'
        print >> gnu_fp, 'set key top left'
        print >> gnu_fp, 'set tics out'
        self.write_extra(gnu_fp, self.extra)

        print >> gnu_fp, 'set xtics (%s)' % ", ".join(self.format_tics(axis_data=self.x_data, axis_size=self.plot_width, format_type="size"))
        print >> gnu_fp, 'set ytics (%s)' % ", ".join(self.format_tics(axis_max=self.y_max, format_type=self.y_type, scale_type=self.y_axis_type))

        y_min = 0
        if self.y_axis_type == "log":
            print >> gnu_fp, "set log y"
            y_min = 1

        x_min = 0
        if self.x_axis_type == "log":
            print >> gnu_fp, "set log x"
            x_min = 1

        # Setting x-range and y-range.
        print >> gnu_fp, "set xrange [%d:%d]" % (x_min, max(2,self.get_buffered_x_max(format_type=self.y_type)))
        print >> gnu_fp, "set yrange [%d:%d]" % (y_min, max(2, self.get_buffered_y_max(format_type=self.y_type)))

        i = 0
        plot_str = 'plot '
        plot_strs = []
        for p in dat_files:
            i += 1
            (procs, tag, dat_filename) = p
            title = "%s procs (Tag: %s)" % (procs, format_tag(tag))
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

                    show_errors = self.settings.show_errors and agg_name == "avg"

                    lp = LinePlot(test_name=test, title_help=agg_name, test_type="single", output_folder=self.output_folder, extra=self.settings.plot_extra, show_errors=show_errors)
                    lp.set_prefix( run_type[0] )
                    lp.set_height(self.settings.plot_height)
                    lp.set_width(self.settings.plot_width)

                    if run_type[0] == "scale":
                        lp.set_y_type("scale")
                    else:
                        lp.set_y_type(self.y_type)

                    lp.set_axis_type(self.settings.x_axis_type, self.settings.y_axis_type)
                    data = getattr(self.data, "agg_"+run_type[1])[test]
                    error = False
                    for procs in data:
                        for tag in data[procs]:
                            try:
                                lp.add_data(procs, tag, data[procs][tag][agg_name])
                            except KeyError:
                                #print "KeyError", procs, tag, test, data[procs][tag].keys()
                                error = True
                    if not error:
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
                sp = ScatterPlot(test_name=test, test_type="single", output_folder=self.output_folder, extra=self.settings.plot_extra)
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
        formatted_tags.append( format_tag(tag) )

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
