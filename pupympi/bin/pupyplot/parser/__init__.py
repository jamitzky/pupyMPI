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
import csv, re

PROCS_RE = re.compile(".*\.([0-9]+)procs.*")

class Parser(object):
    """
    Contains the actual parser more or less copied from the earlier version
    of pupyplot.py. The parser will accept a list of tupes where each tuple
    has the form of:

        (tag, csv-filepath)

    This means that all the tag regexps etc is not here. Neither is the actual
    script for writing the parsed data to a handle.
    """
    def __init__(self):
        """
        Initialize the parser.
        """

        # Contains all the parsed data. There is no easy way to filter
        # the data for tetst name etc.
        self.data = []

    def parse_file(self, tag, filepath):
        reader = csv.reader(open(filepath, 'r'))

        # Find the number of procs from the filename.
        match = PROCS_RE.match(filepath)
        nodes = int(match.groups()[0])

        for row in reader:
            row = map(lambda x: x.strip(), row)

            if self.row_is_header(row): continue

            if self.row_is_comment(row): continue

            # Fetch the data through a method. This is done
            # as the data formats we support differ a lot
            # and it is messy to handle this logic here.
            try:
                datasize, total_time, iteration_time, throughput, runtype, time_min, time_max = self.from_extract_data(row)
                throughput = throughput*1024*1024
                data_item = tag, runtype, datasize, total_time, iteration_time, throughput, time_min, time_max, nodes

               #print ""
               #print "datasize:".ljust(40), datasize
               #print "total_time:".ljust(40), total_time
               #print "iteration_time:".ljust(40), iteration_time
               #print "throughput:".ljust(40), throughput
               #print "runtype:".ljust(40), runtype
               #print "time_min:".ljust(40), time_min
               #print "time_max:".ljust(40), time_max
               #print "nodes:".ljust(40), nodes

                self.data.append(data_item)
            except Exception, e:
                print "Found exception", e

    def from_extract_data(self, row):
        # Unpack data
        datasize = row[0]
        total_time = row[2]
        iteration_time = row[3]
        throughput = 0
        runtype  = ""
        time_min = 0
        time_max = 0

        if len(row) == 10:
            # new format
            time_min = row[4]
            time_max = row[5]
            try:
                throughput = row[6]
            except:
                throughput = 0

            runtype = row[8]
        elif len(row) == 8:
            # old format. Wasting memory due to lack of coding stills by CB
            time_min = iteration_time
            time_max = iteration_time

            throughput = row[4]
            runtype = row[6]
        elif len(row) == 7:
            runtype = row[5]
            throughput = row[4]

        else:
            print "WARNING: Found a row with a strange number of rows:", len(row)
            print "\t", ",".join(row)
            return None

        # There are None values in throughput. Detect this can insert -1 instead
        try:
            throughput = float(throughput)
        except ValueError:
            throughput = -1.0

        # Post fix data
        runtype = runtype.replace("test_","")

        return int(datasize), float(total_time), float(iteration_time), throughput, runtype, float(time_min), float(time_max)

    def row_is_header(self, row):
        """
        Test if a row is considered a header row. The caller
        will probably discard the row, but nothing is done
        here in the function.
        """
        # A header does not start with a number
        return len(row) < 2 or not row[0].isdigit()

    def row_is_comment(self, row):
        return row[0].startswith("#")
