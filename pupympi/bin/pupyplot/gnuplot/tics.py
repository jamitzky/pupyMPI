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

__all__ = ('datasize', 'scale', 'time', 'throughput', 'number', )

def _spread(p_min, p_max, no):
    skip = (p_max - p_min) / float(no)
    p = p_min
    final_points = [p_min]
    
    for _ in range(no-1):
        p += skip
        final_points.append(p)
        
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
    return _format_datasize(bytecount, decimals=2)+"/s"

def _format_scale(scale): # {{{2
    return "%.0f" % scale

def _format_number(number):
    return "%d" % int(number)

def _format_time(usecs): # {{{2
    border_list = [ (1000, 'us'), (1000000, 'ms'), (1000000000, 's'),]
    for i in range(len(border_list)):
        bl = border_list[i]
        if usecs < bl[0]:
            if i > 0:
                usecs = usecs / border_list[i-1][0]
            return "%.0f%s" % (usecs, bl[1])

def _ensure_tic_space(points, axis_type, fit_points, discrete):
    """
    A helper function removing tics if we figure there is not
    enough room for them.
    
    ..note:: The discrete parameter is not used. 
    """
    def generate_bump_points(start, bump, end):
        points = [start]
        
        while start < end:
            start += bump
            points.append(start)
            
        return points
    
    p_min = min(points)
    p_max = max(points)
    
    if True:
        log_base = 32 # 10 in case of normal numbers. 
        extender = 32
    else:
        log_base = 10
        extender = 4
        
    if axis_type == 'lin':
        skip_size = p_max - p_min
        skip_bump = (log_base**(math.floor(math.log(skip_size, log_base))))/extender
        
        points = generate_bump_points(p_min, skip_bump, p_max)
    elif axis_type == 'log':
        pass
    
        # Remove 0
        try:
            points.remove(0)
        except:
            pass
        
    while len(points) > fit_points:
         points = points[::2]
    
    return points
        
def _simple_formatter(points, formatter, axis_type, fit_points, discrete=False):    
    data_points = _ensure_tic_space(points, axis_type, fit_points, discrete)
    # Return a list with the data points formatted.
    tics = []
    for item in data_points:
        label = formatter(item)
        tics.append("'%s' %d" % (label, item))
    return ', '.join(tics)
    
def scale(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_scale, axis_type, fit_points)

def datasize(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_datasize, axis_type, fit_points, discrete=True)

def time(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_time, axis_type, fit_points)

def throughput(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_throughput, axis_type, fit_points)

def number(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_number, axis_type, fit_points, discrete=True)
