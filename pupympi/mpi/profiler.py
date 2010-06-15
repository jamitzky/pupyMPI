#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
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
#
import sys
import threading, thread, inspect

class Profiler:

    __shared_state = {} # Shared across all instances
    # singleton check
    def __init__(self, *args, **kwargs):
        self.__dict__ = self.__shared_state 

        #self._LOG_FILENAME = constants.

        self.events = {}
        self.eventlock = threading.Lock()

    def start(self):
        print "starting built-in profiler"
        sys.setprofile(self.trace_event)
        threading.setprofile(self.trace_event)

    def stop(self):
        print "stopping built-in profiler"
        sys.setprofile(None)
        threading.setprofile(None)

    def trace_event(self, frame, event, arg):
        if event == "call":
            with self.eventlock:
                print "[%d] :: call (%s) %s" % (thread.get_ident(), frame.f_code.co_filename, frame.f_code.co_name)
        if event == "c_call":
            with self.eventlock:
                print "[%d] :: C call (%s) %s.%s" % (thread.get_ident(), frame.f_code.co_filename, arg.__module__, arg.__name__)
        return self.trace_event

    def dump_stats(self):
        print "dumping stats..."

