#!/usr/bin/env python
# encoding: utf-8
"""
common.py

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import unittest
import array

def 

baseset = "abcdefghijklmnopqrstuvwxyz"

def gen_testset(size):
    data = array.array('b')
    for x in xrange(0, size):
        data.append(ord(baseset[x % len(baseset)]))
    return data
    
def gen_reductionset(size):
    raise Exception("Method not implemented")
    pass


class commonTests(unittest.TestCase):
    def setUp(self):
        pass
        
    def test_gen_testset(self):
        self.assertEqual(1024, len(gen_testset(1024)))

    def test_gen_reductionset(self):
        pass # TODO implement

if __name__ == '__main__':
    unittest.main()