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

import csv
from os import path
csv.register_dialect('tags', delimiter=':', quoting=csv.QUOTE_ALL)

def write_tag_file(tags, filename):
    """
    A simple way to write a filemapper file
    based on a tag list and basic file name.
    """    
    if not filename.endswith(".tagmapper"):
        filename += ".tagmapper"
    
    alltags = {}
    for tag in tags:
        alltags[tag] = tag
    
    if path.exists(filename):
        base = get_tag_mapping(filename)
        
        for k in base:
            v = base[k]
            alltags[k] = v
            
    writer = csv.writer(open(filename, "wb"), 'tags')
    
    # Write the tags
    for k in alltags:
        v = alltags[k]
        writer.writerow( (k, v))
            
def get_tag_mapping(filename):
    mapping = {}
    reader = csv.reader(open(filename, "r"), 'tags')
    for row in reader:
        mapping[row[0]] = row[1]
        
    return mapping