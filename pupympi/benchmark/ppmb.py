#!/usr/bin/env python2.6
# encoding: utf-8
"""
ppmb.py - Benchmark runner.

Usage: MPI program - run with mpirun


Created by Jan Wiberg on 2009-08-13.
"""

import sys
import getopt
import mpi

import common
import single
import collective
import parallel


help_message = '''
The help message goes here.
'''


def runsingletest(test):
    results = {}
    for size in common.size_array:        
        results[size] = test(size, None)
        
    return results

def testrunner():
    # TODO generalize for several modules.
    testlist = [c for c in dir(single) if c.startswith("test_")] 
    resultlist = {}
    #print funclist
    for fstr in testlist:
        f = getattr(single, fstr)
        result = runsingletest(f)
        resultlist[fstr] = result
    pass
    
    print resultlist

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
