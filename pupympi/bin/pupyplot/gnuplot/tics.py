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
    return "%.2f" % scale

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

def scale(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_scale, axis_type, "int")

def datasize(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_datasize, axis_type, "datasize")

def time(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_time, axis_type, "time")

def throughput(points, axis_type="lin", fit_points=20):
    return _simple_formatter(points, _format_throughput, axis_type, "datasize")

def number(points, axis_type="lin", fit_points=20):
    # Ensure we have only integers
    points = list(set(map(int, points)))
    return _simple_formatter(points, _format_number, axis_type, "int")

AXIS_TYPES = ["lin","log"] # just for reference
DATA_TYPES = ["datasize","time","int"] # just for reference
DATA_BASES = {"datasize":1024.0, "time":1e6, "int":1}

def _simple_formatter(points, formatter, axis_type, data_type):
    data_points = Ticks(points, axis_type, data_type, DATA_BASES[data_type] ).ticks
    # Return a list with the data points formatted.
    tics = []
    for item in data_points:
        label = formatter(item)
        tics.append("'%s' %s" % (label, item))
        
    
    print ', '.join(tics)

    return ', '.join(tics)

class Ticks:
    def __init__(self, y_data, axis_type, data_type, data_base):
        self.ticks = []

        # Convert data using base
        y_data = map(lambda x: 1.0*x/data_base, y_data)
        
        self.y_data = y_data
            
        # Keeps track of the "decade" of the numbers
        decades = 0
        
        # We need a linear scale on the y-axis
        if axis_type == "lin":
    
            # We want something near 8 ticks (we could get more)
            n_step = 8
                        
            # We would like the ticks % 1 == 0 (keeping track of the decade)
            sub_step = 5
            
            # Approximate tick steps 
            app_tick_step = max(y_data)/n_step
            
            # We want a nice tick so we round off the approx. tick
            counter = 0
            while app_tick_step < 1.0:
                app_tick_step *= 10
                counter += 1
                
            app_tick_step = round(app_tick_step)
            
            # if it is smaller than the sub_step, make it bigger
            if app_tick_step < sub_step: app_tick_step *= 10
            
            # Get a better estimate of the approx. step
            app_tick_step = app_tick_step - (app_tick_step % sub_step)
            
            # Get the approx. step back to its original size
            app_tick_step /= 10**counter

            n = app_tick_step    

            # If we are below 1 we are in the "negative" decades
            if max(y_data) > 1.0:
    
                while n > 1.0:
                    decades += 1
                    n /= 10
            
                # Make sure our sub_step is not larger than the approx. step (script would stall)
                while sub_step*(10**decades) > app_tick_step:
                    sub_step /= 10.0
                
                # Calculate actual tick steps as the approx value minus the remainder when
                # we diviede with our preferred step "scaling"
                tick_step = app_tick_step - (app_tick_step % (sub_step*(10.0**decades)))
                
            else:    # we are not below 1
            
                while n < 1.0:
                    decades += 1
                    n *= 10.0
                    
                while sub_step*(10**decades) > app_tick_step:
                    sub_step /= 10.0
                
                # Calculate actual tick steps as the approx value minus the remainder when
                # we diviede with our preferred step "scaling"
                tick_step = app_tick_step - (app_tick_step % (sub_step*(10.0**(-decades))))
            
            # Find the needed number of steps required to conver whole data-range 
            # with the tick steps that we have calculated
            while n_step*tick_step < max(y_data): 
                n_step += 1
    
            # Get the tick-locations
            for    i in range(n_step+1):
                self.ticks.append(i*tick_step)
        else:    # Log scale
            # Some ugly vars
            decades = 0
            n = 1.0
            
            # if the smallest value is below 1 we need to find the origin
            if min(y_data) > n:    
                
                while min(y_data) > n:
                    n *= 10
                    decades += 1
            
                # Get the smallest value on the y-axis
                y_min = 1.0*(10**(decades-1))
            
            
            else:    # Smallest value is above 1 - lets find the origin
    
                while min(y_data) < n:
                    n /= 10
                    decades +=1
                
                # Get the smallest value on the y-axis
                y_min = 1.0/(10**decades)
                
            # Set the first tick
            self.ticks = [y_min]
            
            # this list contain step factors for the log scale
            # first we test if a factor 2 between ticks is enough
            # if not - we increase to 10...
            step_factors = [2,10,100,1e3,1e4,1e5]
            
            # Set initial step size (the step size is the factor between ticks)
            step_size = 0
        
            # Inifinite loop until we have what we need
            while True:
        
                # What we need is an axis with no more that 10 ticks
                for i in range(1,11):
                    
                    # Find next tick location
                    t = y_min*10**(math.log(step_factors[step_size],10)*i)
                    
                    # Save new tick
                    self.ticks.append(t)
    
                    # if the largest tick is larger than the largest data-value 
                    # then our search i complete
                    if t > max(y_data): break    
                    
                if t > max(y_data): break    # escape from outer loop
                
                # if not, change step size and re-initilize ticks 
                step_size = step_size+1
                self.ticks = [y_min]