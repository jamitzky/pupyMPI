#!/usr/bin/env python
# encoding: utf-8
"""
common.py

this file is "deprecated". Its contents should be moved into comm_info.py

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import unittest
import array

# bunch of useless constants for now
N_BARR = 2

size_array = (1,8,1024) # just to test if this works at all

#size_array = (1,2,4,8,32,64,128,512,1024,4096,16384,32768, 65536) # should go to 4mb

def gen_stditerationschedule(max_size):
    return [1000] * len(size_array)
    
baseset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
def gen_testset(size):
    """Generates a test message byte array of asked-for size. Used for single and parallel ops."""
    data = array.array('b')
    for x in xrange(0, size):
        data.append(ord(baseset[x % len(baseset)]))
    return data
    
def gen_reductionset(size):
    """Generates a test message float array of asked-for size. Used for reduction ops."""
    raise Exception("Method not implemented")


class commonTests(unittest.TestCase):
    """Unittests"""
    def setUp(self):
        pass
        
    def test_gen_testset(self):
        self.assertEqual(1024, len(gen_testset(1024)))

    def test_gen_reductionset(self):
        pass # TODO implement

if __name__ == '__main__':
    unittest.main()