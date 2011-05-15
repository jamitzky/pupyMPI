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
from pupyplot.gnuplot import tics
from pupyplot.gnuplot.fonts import Default as FONT_DEFAULT

import os, subprocess


# Choose to limit the available modules by defining an __all__

__all__ = ('GNUPlot', )

class GNUPlot(object):

    def __init__(self, base_filename="", title='', width=8, height=4, xlabel='', ylabel='', xtic_rotate=-45, tics_out=True, key='inside right', font=None, axis_x_type="lin", axis_y_type="lin", axis_x_format="datasize", axis_y_format='time', colors=False, keep_temp_files=False):
        """
        ``base_filename``
             The filename without extension used through this plot. The output file
             will be located in <base_filename>.eps and the gnuplot file will be
             located in <base_filename>.gnu.

             The datafiles will use the <base_filename> as a prefix and will use
             the .dat suffix.
        """
        self.plot_cmd_args = []

        # Point types
        self.pointtypes = 0

        self.height = height
        self.width = width

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

        if True or colors:
            color_str = "color"
        else:
            color_str = "monochrome"
            self.plot_cmd_args.append("-mono")

        # Write the basics
        print >> self.handle, "set term postscript eps enhanced %s font '%s' fontfile '%s' 24 size %d,%d" % (color_str, font.name, font.path, width, height)
        print >> self.handle, 'set output "%s.eps"' % base_filename
        print >> self.handle, 'set title "%s"' % title
        print >> self.handle, 'set xlabel "%s"' % xlabel
        print >> self.handle, 'set ylabel "%s"' % ylabel
        print >> self.handle, 'set xtic nomirror rotate by %d' % xtic_rotate
        print >> self.handle, 'set key %s' % key
        print >> self.handle, 'set pointsize 1.5'

        if axis_x_type == 'log':
            print >> self.handle, 'set log x'

        if axis_y_type == 'log':
            print >> self.handle, 'set log y'

        self.axis_x_type = axis_x_type
        self.axis_y_type = axis_y_type

        if tics_out:
            print >> self.handle, 'set tics out'

    def get_next_pointtype(self):
        """Helper function for finding the point types. They are not sorted!!"""
        reached = self.pointtypes
        types = [0, 4, 5, 6, 7, 3, 2, 1]
        self.pointtypes += 1

        try:
            return types[reached]
        except:
            return reached

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
        self.handle.close()
        args = ["gnuplot", self.handle_filepath]
        #args.extend(self.plot_cmd_args)
        #args.append(self.handle_filepath)
        #print args
        retcode = subprocess.call(args)

    def write_datafile(self, part, xdata, ydata):
        filepath, fh = self.create_temp_file(part)

        if len(xdata) != len(ydata):
            raise Exception('Data not in the same length. This is not bad.')

        for i in range(len(xdata)):
            x = xdata[i]
            y = ydata[i]

            # Check for list to make this function as generic as possible.
            if not hasattr(x, "__iter__"):
                x = [x]

            if not hasattr(y, "__iter__"):
                y = [y]

            for xi in x:
                for yi in y:
                    # Filter 0-data if we have log scales
                    if (xi == 0 and self.axis_x_type == 'log') or (yi == 0 and self.axis_y_type == 'log'):
                        continue

                    print >> fh, "%s    %s" % (xi, yi)

        fh.close()
        return filepath

    def close(self):
        """
        This method cleans up after temporary files (unless told otherwise)
        """
        if not self.keep_temp_file:
            for filepath in self.temp_files:
                os.unlink(filepath)

    def add_serie(self, xdata, ydata, title='Plot title'):
        # We do not add series without data.
        if len(xdata) == 0:
            return

        i = len(self.series)

        def flatten(alist):
            l = []

            for item in alist:
                if hasattr(item, "__iter__"):
                    l.extend(flatten(item))
                else:
                    l.append(item)
            return l

        self.combined_x_data.extend(flatten(xdata))
        self.combined_y_data.extend(flatten(ydata))

        # Write a data file
        datafile = self.write_datafile("data%d" % i, xdata, ydata)
        self.series.append((title, datafile))

    def tics(self):
        def null_filter(tic_list):
            final = []
            for tic in tic_list:
                if tic is not None:
                    final.append(tic)

            return final

        x_points = 20 # This could be "lifted" into a cmd line argument.
        xdata = null_filter(self.combined_x_data)
        ydata = null_filter(self.combined_y_data)

        formatter = getattr(tics, self.axis_x_format, None)

        if formatter:
            xtics = formatter(xdata, fit_points=x_points, axis_type=self.axis_x_type)
            print >> self.handle, "set xtics (%s)" % xtics

        formatter = getattr(tics, self.axis_y_format, None)
        if formatter:
            # Calculate the proper number of fit points.
            y_points = int(float(self.height) / self.width * x_points)

            ytics = formatter(ydata, fit_points=y_points, axis_type=self.axis_y_type)
            print >> self.handle, "set ytics (%s)" % ytics


class LinePlot(GNUPlot):
    def __init__(self, *args, **kwargs):
        super(LinePlot, self).__init__(*args, **kwargs)

        self.series = []

        self.combined_x_data = []
        self.combined_y_data = []

    def plot(self):
        self.tics()

        # Write data to the .gnu file before we continue the plot.
        plot_strs = []
        for serie in self.series:
            title, datafile = serie
            plot_strs.append("'%s' with linespoints pointtype %d title '%s'" % (datafile, self.get_next_pointtype(), title))

        print >> self.handle, "plot " + ", ".join(plot_strs)

        # Call the super plot.
        super(LinePlot, self).plot()

class ScatterPlot(GNUPlot):
    def __init__(self, *args, **kwargs):
        super(ScatterPlot, self).__init__(*args, **kwargs)

        self.series = []

        self.combined_x_data = []
        self.combined_y_data = []

    def plot(self):
        self.tics()

        # Write data to the .gnu file before we continue the plot.
        plot_strs = []
        for serie in self.series:
            title, datafile = serie
            plot_strs.append("'%s' pointtype %d title '%s'" % (datafile, self.get_next_pointtype(), title))

        print >> self.handle, "plot " + ", ".join(plot_strs)

        # Call the super plot.
        super(ScatterPlot, self).plot()
