#!/usr/bin/env python
# encoding: utf-8
"""
processloaders.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os


def popenssh(args):
    pass
    
def ssh(args):
    pass
    
def popen(host, arguments):
    if host == "localhost":             # This should be done a bit clever
        from subprocess import Popen
        p = Popen(arguments)
    else:
        raise InputException("This processloader can only start processes on localhost.")
    
