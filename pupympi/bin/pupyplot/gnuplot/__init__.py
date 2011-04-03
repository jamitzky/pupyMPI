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

# HACKING! Making it possible to import everything from this module
from pupyplot.gnuplot.color import *
from pupyplot.gnuplot import tics
from pupyplot.gnuplot.fonts import Default as FONT_DEFAULT

import os, subprocess


# Choose to limit the available modules by defining an __all__

__all__ = ('GNUPlot', )

class GNUPlot(object):
    
    def __init__(self, base_filename="", title='', width=8, height=4, xlabel='', ylabel='', xtic_rotate=-45, tics_out=True, key='top left', font=None, axis_x_type="lin", axis_y_type="lin", axis_x_format="datasize", axis_y_format='time', keep_temp_files=False):
        """
        ``base_filename`` 
             The filename without extension used through this plot. The output file 
             will be located in <base_filename>.eps and the gnuplot file will be
             located in <base_filename>.gnu. 
             
             The datafiles will use the <base_filename> as a prefix and will use
             the .dat suffix.
        """
        # Save the user supplied arguments
        self.base_filename = base_filename
        self.keep_temp_file = keep_temp_files
        
        # Setup variables to keep track on possible temporary files. 
        self.temp_files = []
        
        # Open the .gnu handle file. 
        file_path, file_handle = self.create_temp_file(self.base_filename, ".gnu")
        self.handle = file_handle
        self.handle_filepath = file_path
        
        # Set the formatter elements
        self.axis_x_format = axis_x_format
        self.axis_y_format = axis_y_format
        
        # Find the default font and use that if there is no font.
        if not font:
            font = FONT_DEFAULT()
        
        # Write the basics
        print >> self.handle, "set term postscript eps enhanced color font '%s' fontfile '%s' 24 size %d,%d" % (font.name, font.path, width, height)
        print >> self.handle, 'set output "%s.eps"' % base_filename
        print >> self.handle, 'set title "%s"' % title
        print >> self.handle, 'set xlabel "%s"' % xlabel
        print >> self.handle, 'set ylabel "%s"' % ylabel
        print >> self.handle, 'set xtic nomirror rotate by %d' % xtic_rotate
        print >> self.handle, 'set key %s' % key
        
        if axis_x_type == 'log':
            print >> self.handle, 'set log x'

        if axis_y_type == 'log':
            print >> self.handle, 'set log y'
        
        if tics_out:
            print >> self.handle, 'set tics out'

    def create_temp_file(self, file_part, extension=".dat"):
        """
        Create a temporary file, add a prefix and extension
        and keep track of it.
        """
        # Should we add the prefix
        if not file_part.startswith(self.base_filename):
            file_part = self.base_filename + file_part
        
        file_part += extension
        
        # Keep track of the file for later deletion
        self.temp_files.append(file_part)
        
        fh = open(file_part, "w")
        return file_part, fh
    
    def plot(self):
        args = ["gnuplot", self.handle_filepath]
        subprocess.Popen(args)
            
    def write_datafile(self, part, xdata, ydata):
        filepath, fh = self.create_temp_file(part)
        
        if len(xdata) != len(ydata):
            raise Exception('Data not in the same length. This is not bad.')
        
        for i in range(len(xdata)):
            print >> fh, "%s    %s" % (xdata[i], ydata[i])
                
        fh.close()
        return filepath
    
    def close(self):
        """
        This method cleans up after temporary files (unless told otherwise)
        """
        if not self.keep_temp_file:
            for filepath in self.temp_files:
                os.unlink(filepath)

class LinePlot(GNUPlot):
    def __init__(self, *args, **kwargs):
        super(LinePlot, self).__init__(*args, **kwargs)
        
        self.series = []
        self.xdata = None
        self.ydata = None
        
    def add_serie(self, xdata, ydata, title='Plot title'):
        i = len(self.series)
        self.xdata = xdata
        self.ydata = ydata
        
        # Write a data file
        datafile = self.write_datafile("data%d" % i, xdata, ydata)
        self.series.append((title, datafile))
        
    def tics(self):
        formatter = getattr(tics, self.axis_x_format, None)
        if formatter:
            xtics = formatter(self.xdata)
            print >> self.handle, "set xtics (%s)" % xtics

        formatter = getattr(tics, self.axis_y_format, None)
        if formatter:
            ytics = formatter(self.ydata)
            print >> self.handle, "set ytics (%s)" % ytics
    
    def plot(self):
        self.tics()
        
        # Write data to the .gnu file before we continue the plot.
        plot_strs = []
        for serie in self.series:
            title, datafile = serie 
            plot_strs.append("'%s' with linespoints title '%s'" % (datafile, title))
             
        print >> self.handle, "plot " + ", ".join(plot_strs)
        
        # Call the super plot.
        super(LinePlot, self).plot()
