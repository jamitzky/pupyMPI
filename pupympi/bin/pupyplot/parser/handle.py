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

"""
Functions for creating and manipulating handle files
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

from os import path

class Handle(object):
    """
    The main way to interact with the handle file. It is possible to 
    add / remove / edit data to the file and have it written to the
    file system.
    """
    
    def __init__(self, filename='parsed.pickled', dataobj=[]):
        self.dataobj = dataobj
        self.filename = filename
        
        # Load the file if it exists on the disk
        self.reload()
        
    def save(self):
        pickle.dump(self.dataobj, open(self.filename, "w"), pickle.HIGHEST_PROTOCOL)
        
    def reload(self):
        if path.isfile(self.filename):
            self.dataobj = pickle.load(open(self.filename, "r"))
