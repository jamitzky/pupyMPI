#!/usr/bin/env python
# encoding: utf-8
"""
processloaders.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import subprocess
from exceptions import MPIException

# TODO Output redirect. Log files?

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"
    
def popenssh(host, arguments):
    """Mixed Popen/SSH process starter. Uses Popen for localhost hosts, otherwise ssh"""
    if _islocal(host):
        p = popen(host, arguments)
    else:
        ssh(host, arguments)
    
def ssh(host, arguments):
    """SSH process starter. Non-loadbalancing."""
    sshexec = ["ssh"] + [host] + arguments
    print sshexec
    p = subprocess.Popen(sshexec, stderr=subprocess.PIPE)
    errdata = p.communicate()[1]
    print "SSH PROCESS RETURN:\n",errdata
    
def popen(host, arguments):
    if _islocal(host):
        p = subprocess.Popen(arguments)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)
    
