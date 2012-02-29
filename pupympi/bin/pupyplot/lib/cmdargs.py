#!/usr/bin/env python
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

from optparse import OptionParser, OptionGroup
import sys, os

pupyplotpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
binpath = os.path.dirname(os.path.abspath(pupyplotpath))
mpipath = os.path.dirname(os.path.abspath(binpath))

sys.path.append(mpipath)
sys.path.append(pupyplotpath)
sys.path.append(binpath)

from mpi import constants
from pupyplot.parser.handle import Handle
from pupyplot.lib.aggregate import AGGR_USER_CHOICES

# Define a function for building a simple parser useable in multiple
# scripts.
DATA_CHOICES = {
    'datasize' : 'Data size',
    'total_time'  :'Total time',
    'avg_time'  : 'Average time',
    'min_time' : 'Minimum time',
    'max_time' : 'Maximum time',
    'throughput' :'Throughput',
    'nodes' : 'Number of participants',
}

SERIES_CHOICES = DATA_CHOICES.keys()
SERIES_CHOICES.append("none")
 
def plot_parser():
    DATA_FILTERS = ['zero', ]
    COLOR_SCHEMES = []

    usage = """usage: %prog [options] datafile"""

    parser = OptionParser(usage=usage, version="pupyplot version %s" % (constants.PUPYVERSION))

    # A dict containing all the defined optionsgroups. Returning this as a dict will enable
    # new groups to emerge without breaking current code using this. It will also force people
    # to mention the needed group very explicitly
    groups = {}

    # Basis information: logging (and help will also be here.
    parser.add_option("-q", "--quiet", dest="verbose", action="store_false", help="Will not output anything. You should still be able to see the supressed output in the log file.")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Verbose mode. This will output a lot of messages useful when debugging. ")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="Enters debug mode. Will output a lot more to stdout and logfile. No output is written to stdout unless the -v flag is also used")
    parser.add_option("-l", "--log-file", dest="logfile", help="The location of the logfile. If the file exists the contents will be overwritten without prompting. If the file does not exists the file will be created if possible. ")

    # The most import
    parser.add_option('--x-data', default='datasize', choices=DATA_CHOICES.keys(), dest='x_data', help='Which data to plot on the x axis. Defaults to %default. Choices are: ' + ",".join(DATA_CHOICES.keys()))
    parser.add_option('--y-data', default='avg_time', choices=DATA_CHOICES.keys(), dest='y_data', help='Which data to plot on the y axis. Defaults to %default. Choices are: ' + ",".join(DATA_CHOICES.keys()))
    parser.add_option('--series-column', default='nodes', choices=SERIES_CHOICES, dest='series_col', help='Which column should be used to seperate different series. Defaults to %default. Choices are: ' + ",".join(DATA_CHOICES.keys()) + " or none. If you supply 'none' there will only be one serie per tag")

    format_group = OptionGroup(parser, "Formatting", "Basic formatting options. These allow you to control a number of elements in the final plot. These options will not change the plot in any other ways than layout and should therefore not be primary concern. ")
    
    format_group.add_option("--x-axis-use-data-points", action="store_true", default=False, dest="x_axis_use_data_points")
    format_group.add_option("--tag-mapper", dest='tag_mapper', default=None, help='The file containing the tag mapping. This is useful when you do not wish to keep the default names for data series. The readdata.py script will create such a file so it is simple to replace unwanted names. The script will try to find the file from the handle file name so normally you should not supply anything.' )

    parser.add_option_group(format_group)
    groups['format'] = format_group

    plot_group = OptionGroup(parser, "Plotting", "More specific plot options. These can possible change the output a lot, clipping the image etc")
    plot_group.add_option('--plot-height', type=int, dest='height', default=6, help='The height of the plot. Defaults to %default')
    plot_group.add_option('--plot-width', type=int, dest='width', default=None, help='The width of the plot. Defaults to 4/3 of the height.')
    plot_group.add_option('--axis-x-type', dest='axis_x_type', default="lin", choices=['lin', 'log'], help='The x axis type. Choices are lin or log. Defaults to %default. If log is select 0-indexes data will be removed from the plot')
    plot_group.add_option('--axis-y-type', dest='axis_y_type', default="lin", choices=['lin', 'log'], help='The y axis type. Choices are lin or log. Defaults to %default. If log is select 0-indexes data will be removed from the plot')
    plot_group.add_option('--plot-errors', dest='plot_errors', default=False, action='store_true', help='Show errorbars if the plot data supports it')

    parser.add_option_group(plot_group)
    groups['plot'] = plot_group

    # Data handling
    data_group = OptionGroup(parser, "Data handling", "Control all the data controls. Through these it is possible to filter the data, average the data with different functions etc. ")
    data_group.add_option('--x-data-filter', default=[], action='append', dest='x_data_filter', choices=DATA_FILTERS, help='Filter the data plotable on the x axis. Possible choices are ' + ','.join(DATA_FILTERS) + '. Defaults to %default. See the next parameter for a more detailed description')
    data_group.add_option('--y-data-filter', default=[], action='append', dest='y_data_filter', choices=DATA_FILTERS, help='Filters the data plotable on the y axis. Same choices and default variables as on the x axis. It it possible to specify this options multiple times thereby adding multiple filters. These will be executed in the same order as supplied on the command line.')
    data_group.add_option('--raw-filters', default='', dest='raw_filters', help='Enter a number of semicolon seperated raw filters to apply on the data. This can be in the form of VAR:VAL1,VAL2. For example you can include only the data with a node count of 4 or 32 by "--raw-filters=node:4,32')
    data_group.add_option('--y-data-aggregate', default='min', dest='y_data_aggr', choices=AGGR_USER_CHOICES, help='Aggregates the y data according to some function. Default is %default. Choices are ' + ','.join(AGGR_USER_CHOICES))
    data_group.add_option('--test-filter', default="", dest="test_filter", help="A comma sep list with the test the system should plot.")
    parser.add_option_group(data_group)
    groups['data'] = data_group

    # Extending your plot
    extending_group = OptionGroup(parser, 'Extending the plots', 'Options allowing you to extend the generated plots beyond the somewhat limited possibilites of the plot script')
    extending_group.add_option('--keep-temp-files', dest='keep_temp', action='store_true', default=False, help='Do not delete the generated files. This will allow you to edit the .dat and .gnu files and customize your plot this way')
    extending_group.add_option('--extra-plot-lines', action='append', default=[], help='Insert extra plot lines. This means that it is possible to insert a guideline by entering log(x) or x*2')
    parser.add_option_group(extending_group)
    groups['extending'] = extending_group

    return parser, groups

def parse(parser):
    """
    Parses the above parser (and more maybe) and handle other elements like
    creating Loggers with the proper parameter etc. This method should be
    used to avoid a lot of duplicate code.
    """
    options, args = parser.parse_args()

    # Look for a different tag mapper.
    if len(args) != 1:
        parser.error("No data file supplied!")
        
    handle_file = args[0]
    if not Handle.valid_handle_file(handle_file):
        parser.error("Invalid data file")

    # Check that the supplied tag mapper is actually a file
    if options.tag_mapper and not os.path.isfile(options.tag_mapper):
        parser.error("No such tag mapper file: %s" % options.tag_mapper)
    
    if not options.tag_mapper:
        # Look for a default tag mapper
        potential_mapper = handle_file + ".tagmapper"
        if os.path.isfile(potential_mapper):    
            options.tag_mapper = potential_mapper

    # Clean the filter test.
    options.test_filter = filter(None, [s.strip().lower() for s in options.test_filter.split(",")])
    
    # Create a negative test case if we try to use datasize. This is not supported by barrier. 
    if "datasize" in (options.x_data, options.y_data):
        options.test_filter.append(":barrier")
        
    # Setup a logger based on the arguments about. This might seem stupid
    # as it is not returned from the call, but as the Logger is a singleton
    # it is possible to do a simple Logger() call later.
    from mpi.logger import Logger
    logfile = "pupyplot.log"
    if options.logfile:
        logfile = options.logfile

    verbosity = 1
    if options.debug:
        verbosity = 3
    elif options.verbose:
        verbosity = 2

    Logger(logfile, "pupyplot", options.debug, verbosity, not options.verbose)
    
    # Normalize the raw filters. 
    raw_filters = []
    for f in filter(None, [f.strip() for f in options.raw_filters.split(";")]):
        # For now we only have one filter type (equal). We identify this by
        # a simple string. Parser people would probably not like this
        t = f.split(":")
        vals = filter(None, [f.strip() for f in t[1].split(",")])
        if len(t) == 2:
            raw_filters.append( (t[0], "EQ", vals))
        
    options.raw_filters = raw_filters

    return options, args
