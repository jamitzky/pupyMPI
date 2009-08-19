#!/usr/bin/env python2.6
# encoding: utf-8
"""
processloaders.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys, os, subprocess, select
from mpi.exceptions import MPIException
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

def build_env():
    return {"PATH": "/opt/local/bin/"}

def ssh(host, arguments):
    global remote_list
    logger = Logger()
    """SSH process starter. Non-loadbalancing."""
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../"
    sshexec = ["ssh"] + [host] + ["PYTHONPATH=" + python_path ]+ arguments 
    logger.debug("Exec: %s" % (' '.join(sshexec)))
    p = subprocess.Popen(sshexec, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=build_env())
    process_list.append(p)
    return p
    
def popen(host, arguments):
    global process_list
    logger = Logger()

    if _islocal(host):
        print str(arguments)
        p = subprocess.Popen(arguments, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=build_env()
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)

def wait_for_shutdown(process_list):
    logger = Logger()
    while process_list:
        for p in process_list:
            returncode = p.poll()
            if returncode is None:
                process_list.remove( p )
            else:
                logger.debug("Process exited with status: %d" % returncode)

        time.sleep(1)
