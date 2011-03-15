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
        reader = csv.reader(open(filename))
        
        for row in reader:
            row = map(lambda x: x.strip(), l)
            
            if self.row_is_header(row): continue
        
            if self.row_is_comment(row): continue

            # Fetch the data through a method. This is done
            # as the data formats we support differ a lot
            # and it is messy to handle this logic here.
            try:
                datasize, iteration_time, throughput, runtype, time_min, time_max = self.from_extract_data(row)
                data_item = tag, datasize, iteration_time, throughput, runtype, time_min, time_max
                self.data.append(data_item)      
            except Exception, e:
                print "Found exception", e 
                
        reader.close()
        
    def from_extract_data(self, row):
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
            return None
            
        return datasize, iteration_time, throughput, runtype, time_min, time_max
            

    def row_is_header(self, row):
        """
        Test if a row is considered a header row. The caller
        will probably discard the row, but nothing is done
        here in the function.
        """
        # A header does not start with a number
        return not row[0].isdigit()
    
    def row_is_comment(self, row):
        return row[0].startswith("#")