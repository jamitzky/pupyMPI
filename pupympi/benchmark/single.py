#!/usr/bin/env python
# encoding: utf-8
"""
single.py

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import mpi
import comm_info as c_info
import common

def PingPing(size, iteration_schedule = None):
    s_tag = 1
    r_tag = s_tag if c_info.select_tag else common.MPI_ANY_TAG
    dest = -1
    if c_info.rank == c_info.pair0:
        dest = c_info.pair1
    elif c_info.rank == c_info.pair1:
        dest = c_info.pair0
    
    source = dest if c_info.select_source else common.MPI_ANY_SOURCE   
    
def PingPong():
    pass

def main():
    pass # this should never run


if __name__ == '__main__':
    main()

