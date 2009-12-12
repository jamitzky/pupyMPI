
#!/usr/bin/env python2.6
# encoding: utf-8
"""
pupymark.py - Benchmark runner.

Usage: MPI program - run with mpirun

Created by Jan Wiberg on 2009-08-13.
"""
from time import localtime, strftime

import sys,pprint,getopt, datetime
from mpi import MPI
from mpi import constants

import comm_info as ci
import single
import collective
import parallel


help_message = '''
The help message goes here.
'''

def testrunner(fixed_module = None, fixed_test = None, limit = 2**32):
    """
    Initializes MPI, the shared context object and runs the tests in sequential order.
    The fixed_module parameter forces the benchmark to run just that one benchmark module
    """
    modules = [single, parallel, collective]
    testlist = []
    resultlist = {}

    mpi = MPI()
    root = mpi.MPI_COMM_WORLD.rank() == 0
    
    # print ("Limitation parameters, fixed_module = %s and fixed_test = %s" % (fixed_module, fixed_test))

    def run_benchmark(module, test):
        """Runs one specific benchmark in one specific module, and saves the timing results."""
        results = []

        ci.log("%s - %s" % (module.__name__, test.__name__)) 
        ci.log("%-10s\t%-10s\t%-10s\t%-10s\t%-10s" % ("#bytes", "#Repetitions", "total[sec]", "t[usec]/itr", "Mbytes/sec"))        
        ci.log("--------------------------------------------------------------------------")
        
        sizekeys = module.meta_schedule.keys()
        sizekeys.sort()
        for size in sizekeys:
            if size > limit:
                continue
                
            total = test(size, module.meta_schedule[size])
            per_it = total / module.meta_schedule[size]
            mbsec = ((1.0 / total) * (module.meta_schedule[size] * size)) / 1048576
            ci.log("%-10s\t%-10s\t%-10s\t%-10s\t%-10s" % (size, module.meta_schedule[size], round(total, 2), round(per_it * 1000000, 2), round(mbsec, 5)))
                
            results.append((size, module.meta_schedule[size], total, per_it, mbsec))
        
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

        ci.select_source = True # required until support for SOURCE_ANY implemented in pupympi
        ci.select_tag = True # required until support for TAG_ANY implemented in pupympi
        

        new_comm = mpi.MPI_COMM_WORLD
        if hasattr(module, "meta_has_meta"):
            if module.meta_separate_communicator:
                if ci.w_num_procs < module.meta_processes_required:
                    raise Exception("Not enough processes active to invoke module %s" % module.__name__)
                    
                new_group = mpi.MPI_COMM_WORLD.group().incl(range(module.meta_processes_required)) # TODO pairs can be implemented here.
                new_comm = mpi.MPI_COMM_WORLD.comm_create(new_group)

            ci.data = ci.gen_testset(min(limit, max(module.meta_schedule))) 
        else:
            raise Exception("Module %s must have metadata present, otherwise you'll get a race condition and other errors." % module.__name__)

        ci.communicator = new_comm
        ci.num_procs = new_comm.size() if new_comm is not constants.MPI_COMM_NULL else -1
        ci.rank = new_comm.rank() if new_comm is not constants.MPI_COMM_NULL else -1
            
    for module in modules:
        if fixed_module is not None and module.__name__ != fixed_module:
            continue

        _set_up_environment(mpi, module)
        
        if ci.rank == -1: # skip unless THIS process participates - we need the environment ready to determine that.
            continue

        for function in dir(module):
            if (fixed_test is None and function.startswith("test_")) or (fixed_test is not None and function.endswith(fixed_test)):
                f = getattr(module, function)
                result = run_benchmark(module, f)
                resultlist[function] = result

    mpi.finalize()
    
    # Output to .csv file
    if root:
        stamp = strftime("%Y-%m-%d %H-%M-%S", localtime())
        filename = "pupymark.output."+stamp+".csv"
        f = open(constants.LOGDIR+filename, "w")
        
        # Column headers for easier reading
        row = "datasize,repetitions,total time,time/repetition,Mb/second,name of test,timestamp of testrun"
        f.write(row+"\n")

        for testname in resultlist:
            testresults = resultlist[testname]            
            
            for res in testresults:
                # Data point
                row = "%i,%i,%f,%f,%f" % (res)
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
    # Parameter parsing disabled until parameter passing through mpirun works
    # if argv is None:
    #     argv = sys.argv
    # try:
    #     try:
    #         opts, args = getopt.getopt(argv[1:], "ho:vm:", ["help", "output=", "module="])
    #     except getopt.error, msg:
    #         raise Usage(msg)
    # 
    #     # option processing
    #     for option, value in opts:
    #         if option == "-v":
    #             verbose = True
    #         if option in ("-h", "--help"):
    #             raise Usage(help_message)
    #         if option in ("-o", "--output"):
    #             output = value
    #         if option in ("-m", "--module"):
    #             module = value
    # 
    # except Usage, err:
    #     print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
    #     print >> sys.stderr, "\t for help use --help"
    #     print >> sys.stderr, "\t Args: " + str(sys.argv)
    #     return 2
    
    # FIXME: haxx it for now (I need the option to run individual modules because everything is too broken to get anywhere)
    
    module = None
    test = None
    limit = 2**32

    for arg in sys.argv:
        if arg.startswith("--module="): # forces a specific test module
            module = arg.split("=")[1]
        if arg.startswith("--test="): # forces one specific test - can be combined with module
            test = arg.split("=")[1]
        if arg.startswith("--limit="): # forces an upper limit on the test data size
            limit = int(arg.split("=")[1])
    testrunner(module, test, limit)
    

if __name__ == "__main__":
    main()
