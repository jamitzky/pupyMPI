#!/usr/bin/env python2.6
# encoding: utf-8
"""
pupymark.py - Benchmark runner.

Usage: MPI program - run with mpirun

Created by Jan Wiberg on 2009-08-13.
"""

import sys,pprint,getopt
from mpi import MPI

import comm_info as ci
import common
import single
import collective
import parallel


help_message = '''
The help message goes here.
'''

def testrunner(fixed_module = None):
    """
    Initializes MPI, the shared context object and runs the tests in sequential order
    """
    modules = [single, parallel, collective]
    testlist = []
    resultlist = {}

    mpi = MPI()
    root = mpi.MPI_COMM_WORLD.rank() == 0

    def test_per_size(module, test):
        results = []
        for size in common.size_array:
            timing = module.do_test(size, test, None)
            results.append((size, round(timing, 5)))

        return results
        
    def _setupCI(mpi, module):
        ci.mpi = mpi
        ci.w_num_procs = mpi.MPI_COMM_WORLD.size()
        ci.w_rank = mpi.MPI_COMM_WORLD.rank()

        ci.select_source = True # required until support implemented in pupympi
        ci.select_tag = True# required until support implemented in pupympi

        new_comm = mpi.MPI_COMM_WORLD
        if hasattr(module, "meta_has_meta"):
            if module.meta_separate_communicator:
                new_group = mpi.MPI_COMM_WORLD.group().incl(range(module.meta_processes_required)) # TODO pairs can be implemented here.
                new_comm = mpi.MPI_COMM_WORLD.comm_create(new_group)

        ci.communicator = new_comm
        # FIXME new_comm will be MPI_COMM_NULL for non participating communicators when we get around to it
        ci.num_procs = new_comm.size()
        ci.rank = new_comm.rank()
            
    for module in modules:
        if fixed_module is not None and module.__name__ != fixed_module:
            continue

        _setupCI(mpi, module)
        
        if ci.rank == -1: # skip unless THIS process participates
            continue
        #print "%s Setting up for %s" % (ci.rank, module.__name__)
        for test in dir(module):
            if test.startswith("test_"):
                f = getattr(module, test)
                #print "module %s, function %s" % (module, f)
                result = test_per_size(module, f)
                #result = 0.0
                resultlist[test] = result

    mpi.finalize()
    
    if root:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(resultlist)

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
    
    for arg in sys.argv:
        if arg.startswith("--module="):
            module = arg.split("=")[1]
        
    testrunner(module)
    

if __name__ == "__main__":
    main()
