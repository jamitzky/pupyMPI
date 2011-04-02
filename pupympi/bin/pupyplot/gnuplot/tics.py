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

import math

    # The functions defined in the __all__ is the actual functions
# for formatting tics. The others hare helpers functions prefixed
# with _ and should not be used directly.

__all__ = ('datasize', 'scale', 'time', 'throughput')

def _spread(points, no):
    points.sort()
    
    length = max(poins) - min(points)
    skip = length / float(no)
    
    last_added = points.pop(0)
    final_points = [last_added]
    
    for point in points:
        diff = point - last_added
        if diff > skip:
            last_added = point
            final_points.append(point)
    
    return final_points

def _format_datasize(bytecount, decimals=2):
    if bytecount == 0:
        return "0 B"
    n = math.log(bytecount, 2)
    border_list = [ (10, "B"), (20, "KB"), (30, "MB"), (40, "GB"), (50, "TB") ]
    fmt_str = "%%.%df%%s" % decimals
    for bl in border_list:
        if n < bl[0]:
            return fmt_str % (float(bytecount) / 2**(bl[0]-10), bl[1])
    return fmt_str % (bytecount, "B")

def _format_throughput(bytecount):
    return self.format_size(bytecount, decimals=1)+"/s"

def _format_scale(self, scale): # {{{2
    return "%.0f" % scale

def _format_time(self, usecs): # {{{2
    border_list = [ (1000, 'us'), (1000000, 'ms'), (1000000000, 's'),]
    for i in range(len(border_list)):
        bl = border_list[i]
        if usecs < bl[0]:
            if i > 0:
                usecs = usecs / border_list[i-1][0]
            return "%.0f%s" % (usecs, bl[1])

def _ensure_tic_space(data_points, axis_type, fit_points):
    """
    A helper function removing tics if we figure there is not
    enough room for them.
    """
    if axis_type == 'lin':
        data_points = spread(data_points, fit_points)
    
    # FIXME: What to do with the log graphs?
    
def _simple_formatter(data_points, formatter, axis_type, fit_points):    
    data_points = _ensure_tic_space(data_points, axis_type, fit_points)
        
    # Return a list with the data points formatted.
    tics = []
    for item in data_points:
        label = formatter(item)
        tics.append("'%s' %d" % (label, item))
    return ', '.join(tics)    
    
def scale(data_points, axis_type="lin", fit_points=20):
    return _simple_formatter(data_points, _format_scale, axis_type, fit_points)

def datasize(data_points, axis_type="lin", fit_points=20):
    return _simple_formatter(data_points, _format_datasize, axis_type, fit_points)

def datasize(data_points, axis_type="lin", fit_points=20):
    return _simple_formatter(data_points, _format_time, axis_type, fit_points)

def throughput(data_points, axis_type="lin", fit_points=20):
    return _simple_formatter(data_points, _format_throughput, axis_type, fit_points)
