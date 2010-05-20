#!/usr/bin/env python2.6
# encoding: utf-8
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

"""
pupymark.py - Benchmark runner.

Usage: MPI program - run with mpirun
"""
from time import localtime, strftime
import sys,pprint,getopt, datetime

from mpi import MPI
from mpi import constants

import comm_info as ci
import single, collective, parallel, special


help_message = '''
The help message goes here.
'''

def testrunner(fixed_module = None, fixed_test = None, limit = 2**32, yappi=False):
    """
    Initializes MPI, the shared context object and runs the tests in sequential order.
    The fixed_module parameter forces the benchmark to run just that one benchmark module
    """
    if yappi: # DEBUG / PROFILE
        built_ins = False # Trace Python built-in functions        
        import yappi # We don't know who is root yet so everybody imports yappi and starts it
        yappi.start(built_ins) # True means also profile built-in functions
    
    modules = [single, parallel, collective, special]
    testlist = []
    resultlist = {}

    mpi = MPI()
    root = mpi.MPI_COMM_WORLD.rank() == 0
    
    def run_benchmark(module, test):
        """Runs one specific benchmark in one specific module, and saves the timing results."""
        results = []

        ci.log("%s processes participating - %s waiting in barrier" %( ci.num_procs, ci.w_num_procs - ci.num_procs ))
        ci.log("%s - %s" % (module.__name__, test.__name__)) 
        ci.log("%-10s\t%-10s\t%-10s\t%-10s\t%-10s" % ("#bytes", "#Repetitions", "total[sec]", "t[usec]/itr", "Mbytes/sec"))        
        ci.log("--------------------------------------------------------------------------")
        
        sizekeys = module.meta_schedule.keys()
        sizekeys.sort()
        for size in sizekeys:
            if size > limit:
                break
                
            total = test(size, module.meta_schedule[size])
            if total is None:
                # Tests returning None are not meant to be run
                # (eg. Barrier for different datasizes does not make sense)
                continue
            if total < 0: # Tests returning negative signals an error
                ci.log("%-10s\t%-10s\t(benchmark failed - datapoint invalid)" % (size, module.meta_schedule[size]))
                results.append((size, module.meta_schedule[size], 0, 0, 0, ci.num_procs))
            else:
                per_it = total / module.meta_schedule[size]
                mbsec = ((1.0 / total) * (module.meta_schedule[size] * size)) / 1048576
                ci.log("%-10s\t%-10s\t%-10s\t%-10s\t%-10s" %  (\
                size, \
                module.meta_schedule[size], \
                round(total, 2), \
                round(per_it * 1000000, 2), \
                round(mbsec, 5)))
                    
                results.append((size, module.meta_schedule[size], total, per_it * 1000000, mbsec, ci.num_procs))
        
        # Show accumulated results for fast estimation/comparison
        alltotal = 0.0
        iterationtime = 0.0
        for r in results:
            alltotal += r[2]
            iterationtime += r[3]
            
        ci.log("--------------------------------------------------------------------------")
        ci.log("(Accumulated)\t   total[sec]:\t%-10s\t%-10s \n" % ( round(alltotal, 2), round(iterationtime * 1000000, 2)))
        return results
        
    def _set_up_environment(mpi, module):
        """Sets up the environment for a given module, by loading meta data from the module itself, and applying it to the comm_info module."""
        ci.mpi = mpi
        ci.w_num_procs = mpi.MPI_COMM_WORLD.size()
        ci.w_rank = mpi.MPI_COMM_WORLD.rank()
        
        ci.select_source = True 
        ci.select_tag = True         

        if hasattr(module, "meta_has_meta"):
            if ci.w_num_procs < module.meta_min_processes:
                raise Exception("Not enough processes active to invoke module %s" % module.__name__)
            
            if module.meta_processes_required == -1:
                processes_required = ci.w_num_procs #e nlist everybody active.
            else:
                processes_required = module.meta_processes_required
                
            new_group = mpi.MPI_COMM_WORLD.group().incl(range(processes_required))
            ci.communicator = mpi.MPI_COMM_WORLD.comm_create(new_group)                
        else:
            raise Exception("Module %s must have metadata present, otherwise you'll get a race condition and other errors." % module.__name__)

        if ci.communicator is not None:
            ci.data = ci.gen_testset(min(limit, max(module.meta_schedule)))
            ci.num_procs = ci.communicator.size() 
            ci.rank = ci.communicator.rank() 
        else:
            ci.num_procs = 0
            ci.rank = -1
        # end of set up environment subfunction
    
    for module in modules:
        if fixed_module is not None and module.__name__ != fixed_module:
            ci.log("Skipping module %s" % module.__name__)
            continue

        _set_up_environment(mpi, module)        
        
        if ci.rank == -1: # hold in barrier unless THIS process participates
            mpi.MPI_COMM_WORLD.barrier()
        else: # participates.
            for function in dir(module):
                if function.startswith("test_"):
                    if fixed_test is not None and not function.endswith(fixed_test):
                        ci.log( "Skipping test %s" % function)
                        continue
                        
                    f = getattr(module, function)
                    result = run_benchmark(module, f)
                    resultlist[function] = result
                    mpi.MPI_COMM_WORLD.barrier() # join the barrier from above.

    mpi.finalize()
    
    # DEBUG / PROFILING
    if yappi:
        if root:
            sorttype = yappi.SORTTYPE_TSUB            
            # yappi.SORTTYPE_TTOTAL: Sorts the results according to their total time.
            # yappi.SORTTYPE_TSUB : Sorts the results according to their total subtime.
            #   Subtime means the total spent time in the function minus the total
            #   time spent in the other functions called from this function.
            stats = yappi.get_stats(sorttype,yappi.SORTORDER_DESCENDING, 50 )

            stamp = strftime("%Y-%m-%d %H-%M-%S", localtime())
            filename = "yappi.%s.%s-%s-%s.sorttype-%s.trace" % (stamp,fixed_module,fixed_test,limit, sorttype)
            f = open(constants.LOGDIR+filename, "w")
            
            for stat in stats:
                print stat
                f.write(stat+"\n")
                
            f.flush()
            f.close()

        yappi.stop()
    
    # Output to .csv file
    if root:
        stamp = strftime("%Y-%m-%d_%H-%M-%S", localtime())
        filename = "pupymark.output."+stamp+".csv"
        f = open(constants.LOGDIR+filename, "w")
        
        # Column headers for easier reading
        row = "datasize,repetitions,total time,time/repetition,Mb/second,nodes,name of test,timestamp of testrun,nodes"
        f.write(row+"\n")

        for testname in resultlist:
            testresults = resultlist[testname]            
            
            for res in testresults:
                # Data point
                try:
                    row = "%i,%i,%f,%f,%f,%i" % (res)
                except:
                    print "Res is",res
                # and we add testname and date for easy pivoting
                row += ",%s,%s" % (testname, stamp)
                f.write(row+"\n")
            # Empty row for easier reading
            f.write("\n")
            
        f.flush()
        f.close()
        

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    
    module = None
    test = None
    limit = 2**32
    yappi = False
    
    for arg in sys.argv:
        if arg.startswith("--module="): # forces a specific test module
            module = arg.split("=")[1]
        if arg.startswith("--test="): # forces one specific test - can be combined with module
            test = arg.split("=")[1]
        if arg.startswith("--limit="): # forces an upper limit on the test data size
            limit = int(arg.split("=")[1])
        if arg.startswith("--yappi"): # forces an upper limit on the test data size
            yappi = True
    testrunner(module, test, limit, yappi)
    

if __name__ == "__main__":
    main()
