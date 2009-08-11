#!/usr/bin/env python
# encoding: utf-8
"""
processloaders.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, subprocess
from exceptions import MPIException
from mpi.logger import Logger

# TODO Output redirect. Log files?

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"
    
def popenssh(host, arguments):
    """Mixed Popen/SSH process starter. Uses Popen for localhost hosts, otherwise ssh"""
    if _islocal(host):
        p = popen(host, arguments)
    else:
        ssh(host, arguments)
    
process_list = []

def ssh(host, arguments):
    global remote_list
    logger = Logger()
    """SSH process starter. Non-loadbalancing."""
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../"
    sshexec = ["ssh"] + [host] + ["PYTHONPATH=" + python_path ]+ arguments 
    logger.debug("Exec: %s" % (' '.join(sshexec)))
    p = subprocess.Popen(sshexec, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process_list.append(p)
    
    
def popen(host, arguments):
    global process_list
    logger = Logger()

    if _islocal(host):
        p = subprocess.Popen(arguments)
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)
    
def gather_io():
    global process_list
    logger = Logger()
    for p in process_list:
        if p.poll():
            logger.debug( "Active remote process: %s" % (p, p.returncode))
        else:
            out,err = p.communicate()
            logger.info( "Active remote process: %s\n\tStdout: %s\n\tStderr: %s" % ( p.returncode, out, str(err)))

def shutdown():
    global process_list
    logger = Logger()
    for p in process_list:
        if p.poll():
            logger.debug("Killing %s" % p)
            p.texrminate()
        
