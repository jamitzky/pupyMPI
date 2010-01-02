#!/usr/bin/env python
# encoding: utf-8
"""
popen_which.py

Created by Jan Wiberg on 2009-09-24.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, subprocess, select, time


def main():
    p = subprocess.Popen(" ssh localhost \" PYTHONPATH=/Users/jan/Documents/DIKU/python-mpi/code/pupympi/bin/../ `which python` -u /Users/jan/Documents/DIKU/python-mpi/code/pupympi/tests/snip_send.py --mpirun-conn-host=Cascais-2.local --mpirun-conn-port=20018 --rank=0 --size=2 --verbosity=1 --debug --log-file=mpi -- \" ", shell=True)
    


if __name__ == '__main__':
	main()

