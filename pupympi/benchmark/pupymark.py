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

Usage: The benchmark runner is an MPI program albeit a complex one. Run it with
        mpirun and more than 4 processes unless you just want the single module
        (consisting only of point-to-point tests)
"""
import time
import datetime
import sys
import platform

from mpi import MPI
from mpi import constants

import comm_info as ci
import single, collective, parallel, special


help_message = '''
The help message goes here.
'''
# Auxillary
def pmap(limit=32):
    """
    pregenerate nice formats for counting bytes
    dict is indexed [bytecount] = (exponent,normalized,longprefix,oneletterprefix)
    eg. {2048 : (11,2,"Kilo","K"), ... }
    """    
    prefixMap = {}    
    for i in range(limit+1):
        pre = ""
        if i < 10:
            div = 1
            pre = ""
        elif i < 20:
            div = 1024
            pre = "Kilo"
        elif i < 30:
            div = 1024**2
            pre = "Mega"
        elif i < 40:
            div = 1024**3
            pre = "Giga"        
        prefixMap[2**i] = (i,(2**i)/div,pre,pre[0:1])   
    return prefixMap


# Main functions

def testrunner(fixed_module = None, fixed_test = None, limit = 2**32):
    """
    Initializes MPI, the shared context object and runs the tests in sequential order.
    
    The fixed_module parameter forces the benchmark to run just that one benchmark module (collection of tests)
    The fixed_test parameter forces the benchmark to run just that one test
    The limit parameter sets the upper bound on size of testdata
    """
    starttime = time.time()
    
    modules = [single, parallel, collective, special]
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
            if limit >= 0: # for positive limits we stop at first size over the limit
                if size > limit:
                    break
            else: # for negative limits we ignore all sizes under the (abs) limit
                if size < abs(limit):
                    continue
                
            total = test(size, module.meta_schedule[size])
            if total is None:
                # Tests returning None are not meant to be run
                # (eg. Barrier for different datasizes does not make sense)
                continue
            if total < 0: # Tests returning negative signals an error
                ci.log("%-10s\t%-10s\t(benchmark aborted - datapoint invalid)" % (size, module.meta_schedule[size]))
                results.append((size, module.meta_schedule[size], 0, 0, 0, ci.num_procs))
            else:
                per_it = total / module.meta_schedule[size]
                # Bytes/second is iterations*iterationsize/totaltime which divided by 1024*1024 is in megabytes
                mbytessec = ((1.0 / total) * (module.meta_schedule[size] * size)) / (1024*1024) 
                ci.log("%-10s\t%-10s\t%-10s\t%-10s\t%-10s" %  (\
                size, \
                module.meta_schedule[size], \
                round(total, 2), \
                round(per_it * 1000000, 2), \
                round(mbytessec, 5)))
                    
                results.append((size, module.meta_schedule[size], total, per_it * 1000000, mbytessec, ci.num_procs))
                
        
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
        
        # TODO: Check on actual required meta tags not the meta meta... my eyes! the abstractions!!!
        if not hasattr(module, "meta_has_meta"):
            raise Exception("Module %s must have metadata present, otherwise you'll get a race condition and other errors." % module.__name__)

        if ci.w_num_procs < module.meta_processes_required:
            raise Exception("Not enough processes active to invoke module %s" % module.__name__)
        
        if module.meta_enlist_all:
            active_processes = ci.w_num_procs #enlist everybody active.
        else:
            active_processes = module.meta_processes_required
            
        new_group = mpi.MPI_COMM_WORLD.group().incl(range(active_processes))
        ci.communicator = mpi.MPI_COMM_WORLD.comm_create(new_group)                

        if ci.communicator is not None:
            if limit > 0:
                testdataSize = min(limit, max(module.meta_schedule))
            else:
                testdataSize = max(module.meta_schedule)
            
            ci.data = ci.gen_testset(testdataSize)
            ci.num_procs = ci.communicator.size() 
            ci.rank = ci.communicator.rank() 
        else:
            ci.num_procs = 0
            ci.rank = -1
        # end of set up environment subfunction
    
    for module in modules:
        
        # Run only the desired modules
        if fixed_module is not None and module.__name__ != fixed_module: # If a specific module is requested and this was not it, we move on
            ci.log("Skipping module %s" % module.__name__)
            continue
        elif fixed_test is not None and ("test_"+fixed_test) not in dir(module): # If a specific test is requested and this module does not contain that test, we move on
            ci.log("Skipping module %s" % module.__name__)
            continue
            
        try:
            _set_up_environment(mpi, module)
        except Exception, e:
            print "Could not setup test environment for module %s. Error: %s" % (module.__name__,e)
            continue
        
        if ci.rank == -1: # hold in barrier unless THIS process participates
            mpi.MPI_COMM_WORLD.barrier()
        else: # participates.
            for function in dir(module):
                if function.startswith("test_"):
                    if fixed_test is not None and not function.endswith(fixed_test):
                        ci.log( "Skipping %s" % function)
                        continue
                        
                    f = getattr(module, function)
                    result = run_benchmark(module, f)
                    resultlist[function] = result
            mpi.MPI_COMM_WORLD.barrier() # join the barrier holding non-participants

    mpi.finalize()
    
    # Output to .csv file
    if root:
        
        sizekeys = [0]+[(2**i) for i in range(23)]
        # Find out what the practical limit was
        actual_limit = 0
        if limit  >= 0:
            for size in sizekeys:
                if size <= limit:
                    actual_limit = size
                    continue
                else:                    
                    break
        else:            
            actual_limit = max(sizekeys)
        
        prefixMap = pmap()
        (c,n,lp,sp) = prefixMap[actual_limit]
        nicelimit = "%i%sB" % (n,sp)
        
        if fixed_module is None:
            nicetype = fixed_test
        else:
            nicetype = fixed_module[0:4] # 4 chars is enough to get the type

        endtime = time.time()
        tdelta = endtime-starttime
        niceelapsed = datetime.timedelta(seconds=tdelta)
        niceend = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime(endtime))
        nicestart = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime(starttime))            
        tstamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(endtime))
        
        filename = "pupymark."+nicetype+"."+str(ci.w_num_procs)+"procs."+nicelimit+"."+tstamp+".csv"
        try:
            f = open(constants.LOGDIR+filename, "w")
        except:            
            raise MPIException("Logging directory not writeable - check that this path exists and is writeable:\n%s" % constants.LOGDIR)
        
        # Test parameters
        header = "# =============================================================\n"
        header += "# pupyMark - pupyMPI benchmarking\n"        
        header += "# \n"
        header += "# %s limit:%s processes:%i\n" % (("test:"+fixed_test if fixed_test is not None else "module:"+fixed_module),nicelimit,ci.w_num_procs)
        header += "# \n"
        header += "# start: %s \n" % nicestart
        header += "# end: %s \n" % niceend
        header += "# elapsed (wall clock): %s \n" % niceelapsed
        # TODO: Show mpirun parameters here
        header += "# \n"
        header += "# pupyMPI version: %s\n" % (constants.PUPYVERSION)        
        header += "# platform: %s (%s)\n" % (platform.platform(),platform.architecture()[0])
        header += "# %s version:%s\n" % (platform.python_implementation(),platform.python_version())
        header += "# =============================================================\n\n"
        f.write(header+"\n")
        
        # Column headers for easier reading
        row = "datasize,repetitions,total time,time/repetition,Mbytes/second,nodes,name of test,timestamp of testrun"
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
                row += ",%s,%s" % (testname, tstamp)
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
    
    for arg in sys.argv:
        if arg.startswith("--module="): # forces a specific test module (collection of tests)
            module = arg.split("=")[1]
        if arg.startswith("--test="): # forces one specific test 
            test = arg.split("=")[1]
        if arg.startswith("--limit="): # forces an upper limit on the test data size
            limit = int(arg.split("=")[1])
    testrunner(module, test, limit)
    

if __name__ == "__main__":
    main()
