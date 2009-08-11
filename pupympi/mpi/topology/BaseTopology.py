#!/usr/bin/env python
# encoding: utf-8
"""
Topology.py

Created by Jan Wiberg on 2009-07-22.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import unittest

# TODO Decide if thats how MPI_TOPO_TEST should be implemented.
MPI_UNDEFINED = 0
MPI_CARTESIAN = 1
MPI_GRAPH = 2

class BaseTopology:
    def __init__(self):
        pass


class TopologyTests(unittest.TestCase):
    def setUp(self):
        pass


if __name__ == '__main__':
    unittest.main()