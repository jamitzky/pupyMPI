#!/usr/bin/env python
# encoding: utf-8
"""
test_pickle.py - just tests some pickle performance.

Created by Jan Wiberg on 2009-09-30.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, time, struct,pprint
import cPickle as pickle
#import pickle

class stuff():
    def __init__(self):
        self.a = 'a'
        self.someint = 42
        
def main():
    iterations = 50000
    data = {"int": 1, "float": 0.42, "string" : "mystring", "listofints": [1,2,3,4,5,6,7,8,9,10], "class": stuff(), "largedict": dict([ (str(n), n) for n in range(100) ])}
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
            pickled = pickle.dumps(pickledata,protocol=-1)
            pickle.loads(pickled)
#            pickle.clear_memo()
        end = time.clock()
        results[d] = (end - start)

    pp = pprint.PrettyPrinter(indent=4)
    
    print "Timings for %d iterations" % iterations
    pp.pprint(results)

    print "Sizes"
    for d in data:
        pickledata = data[d]
        pickled = pickle.dumps(pickledata,protocol=-1)
        pp.pprint( "Size for type %s is %s" % (d, len(pickled)))
        


if __name__ == '__main__':
    main()

