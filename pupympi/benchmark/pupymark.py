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


def runsingletest(test):
    results = []
    for size in common.size_array:
        timing = single.setup_single_test(size, test, None)
        results.append((size, timing))

    print ""
    return results

def testrunner():
    """
    Initializes MPI, the shared context object and runs the tests in sequential order
    """
    mpi = MPI()
    
    ci.mpi = mpi
    ci.communicator = mpi.MPI_COMM_WORLD
    ci.w_num_procs = mpi.MPI_COMM_WORLD.size()
    ci.w_rank = mpi.MPI_COMM_WORLD.rank()
    
    ci.num_procs = ci.communicator.size()
    ci.rank = ci.communicator.rank()
    ci.select_source = True
    ci.select_tag = True
        
    # TODO generalize for several modules.
    testlist = [c for c in dir(single) if c.startswith("test_")] 
    resultlist = {}
    #print funclist
    for fstr in testlist:
        f = getattr(single, fstr)
        result = runsingletest(f)
        resultlist[fstr] = result
    pass

    root = False
    if ci.rank == 0:
        root = True
    mpi.finalize()
    
    if root:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(resultlist)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):    
    testrunner()
    # Parameter parsing disabled until parameter passing through mpirun works
    # if argv is None:
    #     argv = sys.argv
    # try:
    #     try:
    #         opts, args = getopt.getopt(argv[1:], "ho:v", ["help", "output="])
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
    # 
    # except Usage, err:
    #     print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
    #     print >> sys.stderr, "\t for help use --help"
    #     return 2

if __name__ == "__main__":
    main()
