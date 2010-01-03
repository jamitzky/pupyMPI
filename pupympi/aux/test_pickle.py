#!/usr/bin/env python
# encoding: utf-8
"""
test_pickle.py - just tests some pickle performance.

Created by Jan Wiberg on 2009-09-30.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, time, struct,pprint
import cPickle as pickle
import marshal
#import pickle

class stuff():
    def __init__(self):
        self.a = 'a'
        self.someint = 42


def run_pickle():
    """docstring for run_pickle"""
    iterations = 50000
    data = {"int": 1, "float": 0.42, "string" : "mystring", "stringlarge" : "mystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystringmystring", "listofints": [1,2,3,4,5,6,7,8,9,10], "class": stuff(), "largedict": dict([ (str(n), n) for n in range(100) ]), "3int tuple": (1,2,3), "3int list": [1,2,3], "3int dict": {"1": 1, "2":2,"3":3}}
    results = {}

    for d in data:
        pickledata = data[d]
        start = time.clock()
        for i in xrange(iterations):
            if isinstance(pickledata, int ) or isinstance(pickledata, float):
                pickledata += i 
            elif isinstance(pickledata, str):
                pickledata = data[d]
                pickledata += str(i)
            elif isinstance(pickledata, stuff):
                stuff.someint = 42 + i
            pickled = pickle.dumps(pickledata,protocol=-1)
            pickle.loads(pickled)
#            pickle.clear_memo()
        end = time.clock()
        results[d] = (end - start)

    pp = pprint.PrettyPrinter(indent=4)

    print "Timings for %d iterations, pickling. Sum %s" % (iterations, sum([results[r] for r in results]))
    pp.pprint(results)

    print "Sizes"
    for d in data:
        pickledata = data[d]
        pickled = pickle.dumps(pickledata,protocol=-1)
        pp.pprint( "Size for type %s is %s" % (d, len(pickled)))

def run_marshal():
    iterations = 50000
    data = {"int": 1, "float": 0.42, "string" : "mystring", "listofints": [1,2,3,4,5,6,7,8,9,10], "class": stuff(), "largedict": dict([ (str(n), n) for n in range(100) ])}
    results = {}

    for d in data:
        pickledata = data[d]
        try:
            start = time.clock()
            for i in xrange(iterations):
                if isinstance(pickledata, int ) or isinstance(pickledata, float):
                    pickledata += i 
                elif isinstance(pickledata, str):
                    pickledata = data[d]
                    pickledata += str(i)
                pickled = marshal.dumps(pickledata)
                marshal.loads(pickled)            
                
            end = time.clock()
        except ValueError:
            results[d] = "N/A"
            continue
        results[d] = (end - start)

    pp = pprint.PrettyPrinter(indent=4)

    print "Timings for %d iterations, marshalling. Sum %s" % (iterations, sum([results[r] if isinstance(results[r],float) else 0.0 for r in results]))
    pp.pprint(results)

    print "Sizes"
    for d in data:
        pickledata = data[d]
        try:
            pickled = marshal.dumps(pickledata)
        except ValueError:
            pickled = ""
        pp.pprint( "Size for type %s is %s" % (d, len(pickled)))
    """docstring for run_marshal"""

def main():
    run_pickle()
    run_marshal()

if __name__ == '__main__':
    main()

