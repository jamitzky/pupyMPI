#!/usr/bin/env python
# encoding: utf-8
"""
processloaders.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, subprocess
from exceptions import MPIException

# TODO Output redirect. Log files?

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"
    
def popenssh(logger, host, arguments):
    """Mixed Popen/SSH process starter. Uses Popen for localhost hosts, otherwise ssh"""
    if _islocal(host):
        p = popen(logger, host, arguments)
    else:
        ssh(logger, host, arguments)
    
process_list = []

def ssh(logger, host, arguments):
    global remote_list
    """SSH process starter. Non-loadbalancing."""
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../"
    sshexec = ["ssh"] + [host] + ["PYTHONPATH=" + python_path ]+ arguments 
    logger.debug("Exec: %s" % (' '.join(sshexec)))
    p = subprocess.Popen(sshexec, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process_list.append(p)
    
    
def popen(logger, host, arguments):
    global process_list
    if _islocal(host):
        p = subprocess.Popen(arguments)
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)
    
def gather_io(logger):
    global process_list
    for p in process_list:
        if p.poll():
            print "%s exited: %s" % (p, p.returncode)
        else:
            out,err = p.communicate()
            print "%s NOT exited: %s, out %s, ERr %s" % (p, p.returncode, out, err)

def shutdown(logger):
    global process_list
    for p in process_list:
        if not p.poll():
            logger.debug("Killing %s" % p)
            p.kill()
        
