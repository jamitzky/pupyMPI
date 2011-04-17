#!/usr/bin/env python
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

import sys, os, glob

pupyplotpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
binpath = os.path.dirname(os.path.abspath(pupyplotpath))
mpipath = os.path.dirname(os.path.abspath(binpath))

sys.path.append(mpipath)
sys.path.append(pupyplotpath)
sys.path.append(binpath)

from mpi import constants
from pupyplot.parser.handle import Handle
from pupyplot.parser import Parser
from pupyplot.lib import tagmapper

def parse_args():
    from optparse import OptionParser, OptionGroup
    
    usage = """usage: %prog [options] folder1 folder2 ... folderN handlefile
    
        <<folder1>> to <<folderN>> should be folders containing benchmark
        data for comparison."""
    
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))
    parser.add_option('--update-output', '-u', dest='update', action="store_true", default=False, help='Update the output file with new contents. Default will overwrite the file')
    options, args = parser.parse_args()

    if len(args) <= 1:
        parser.error("The script should be called with at leat two positional arguments. First the folders to parse and then the output file")
    
    return options.update, args[-1], args[:-1]

if __name__ == "__main__":
    update, output_file, parse_folders = parse_args()
    
    # Try to remove the file unless we are allowed to update it
    if not update:
        if os.path.isfile(output_file):
            os.unlink(output_file)

    handle = Handle(output_file)
    parser = Parser()
    
    # Find all the CSV files and parse them.
    for folder in parse_folders:
        tag = folder
        csv_files = glob.glob(folder+ "pupymark.*.[0-9]*procs*")
        for csv_file in csv_files:
            parser.parse_file(tag, csv_file)
            
    # Write the tags to a tagmapper
    tagmapper.write_tag_file(parse_folders, output_file)

    # Insert the parsed data in the handle
    handle.dataobj.extend(parser.data)
    
    handle.save()