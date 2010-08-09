'''

 pupyprof.py
 Profiler for pupyMPI

 Based on code from yappi by Sumer Cip

'''
import sys
import threading
import _pupyprof

__all__ = ['start', 'stop', 'write_trace', 'print_stats', 'clear_stats']


'''
 __callback will only be called once per-thread. _pupyprof will detect
 the new thread and changes the profilefunc param of the ThreadState
 structure. This is an internal function please don't mess with it.
'''
def __callback(frame, event, arg):
	_pupyprof.profile_event(frame, event, arg)
	return __callback
'''
...
Args:
timing_sample: will cause the profiler to do timing measuresements
               according to the value. Will increase profiler speed but
               decrease accuracy.
'''
def start():
	threading.setprofile(__callback)
	_pupyprof.start()

def stop():
	threading.setprofile(None)
	_pupyprof.stop()

def clear_stats():
	_pupyprof.clear_stats()

if __name__ != "__main__":
	pass


