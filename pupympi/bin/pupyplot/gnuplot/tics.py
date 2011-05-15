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

from math import floor, log10

# The functions defined in the __all__ is the actual functions
# for formatting tics. The others hare helpers functions prefixed
# with _ and should not be used directly.

__all__ = ('datasize', 'scale', 'time', 'throughput', 'number', )

RECALC_IDENTITY = lambda x: x
RECALC_KB = lambda kb : kb*1024
MSEC_1 = 1000
RECALC_MSEC = lambda sec: sec*MSEC_1

SEC_1 = 1000*MSEC_1
RECALC_SEC = lambda sec: sec*SEC_1

class LinTicker(object):
    """
    This class will generate tics for a linear axis without formatting the numbers. 
    Use the ``get_formatted_tics`` if each tic should be formatted and returned in 
    a list.
    """
    def __init__(self, maxval):
        # The next step require numbers above 1, so while the number if below 1 we multiply
        # with 10 and add this as a factor for reversal.        
        factor = 1
        while maxval < 10:
            maxval *= 10
            factor *= 10

        # Find the possible skip by taking the interval length diving by the
        # number of skips (static to 10).
        interval_length = maxval / 10.0
        
        # Blank out the numbers that are not the leading digit. This is done with string
        # manipulation without any sound reason.
        b = str(int(floor(interval_length)))
        length = int(b[0]) * 10**(len(b)-1)
                    
        tics = []
        t = 0.0
        while t < maxval:
            tics.append(t/factor)
            t += length
            
        # Append a last one. This will go beyond the maxval, but this is a good thing
        # as the plots will look ugly otherwise
        tics.append(t/factor)
        self.tics = tics
    
    def get_formatted_tics(self, unit="", recalc_func=RECALC_IDENTITY, gnuplot=True, clean_precision=True):
        """
        Return a list two 2 tuples where the first tuple element
        is the real value and the second is the formatted value. The
        unit parameter works as a simple string postfix after the
        label have been selected. 
        
        The recalc function is used to convert from a formatted value
        to the real value. For example if you need the real value in
        bytes (for the actual plotting) but the data were given in MB, you
        need to supply a function that multiplies the data with 1024**2.
        """
        # Go sure the formatted tics and find the value with most precision 
        # and use that for all the tics.
        def find_precision(tic):
            st = str(tic)
            if st.find(".") != -1:
                return len(str(tic).split(".")[1])
            elif st.find("e") != -1:
                return int(st.split("e-")[1])
            return 0
            
        max_pres = max([find_precision(tic) for tic in self.tics])
            
        formatted_tics = []
        for tic in self.tics:
            val = recalc_func(tic)

            pres = find_precision(tic)
            if clean_precision: 
                pres = max_pres

            formatted = "%%.%df%s" % (pres, unit) % tic
            t = (formatted, val)
            formatted_tics.append(t)
        
        if gnuplot:
            formatted_tics = ", ".join(["'%s' %s" % t for t in formatted_tics ])
        return formatted_tics
    
class LogTicker(LinTicker):
    def __init__(self, maxval):
        max_exp = int(floor(log10(maxval)))+1
        min_exp = max_exp - 10
        
        self.tics = [10**x for x in range(min_exp+1, max_exp+1)]
        
    def get_formatted_tics(self, *args, **kwargs):
        kwargs["clean_precision"] = False
        return super(LogTicker, self).get_formatted_tics(*args, **kwargs)
        
tickers = {'lin' : LinTicker, 'log' : LogTicker}

def scale(points, axis_type="lin"):
    return number(points, axis_type)

def time(points, axis_type="lin"):
    maxval = max(points)
    
    # Recalc the points from bytes to seconds, so they are easier
    # to format. 
    print int(maxval)
    print SEC_1
    if maxval < SEC_1:      # Use MS
        points = [point/MSEC_1 for point in points]
        unit = 'ms'
        recalc = RECALC_MSEC
    else:                   # Use S
        points = [point/SEC_1 for point in points]
        unit = 's'
        recalc = RECALC_SEC
    
    corrected_maxval = max(points)
    return tickers[axis_type](corrected_maxval).get_formatted_tics(unit=unit, recalc_func=recalc)


def datasize(points, axis_type="lin", unit="KB"):
    # Recalc the points from bytes to kilo bytes, so they are easier
    # to format. 
    points = [point/1024 for point in points]
    maxval = max(points)
    
    return tickers[axis_type](maxval).get_formatted_tics(unit=unit, recalc_func=RECALC_KB)
def throughput(points, axis_type="lin"):
    return datasize(points, axis_type, unit="KB/s")

def number(points, axis_type="lin"):
    # We can only handle lin for now
    maxval = max(points)

if __name__ == "__main__":
    print LogTicker(0.1).get_formatted_tics()

