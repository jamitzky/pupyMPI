#!/usr/bin/env python
# encoding: utf-8
"""
exceptions.py

Created by Jan Wiberg on 2009-08-06.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

# Define exception class
class MPIException(Exception): 
    """Custom exception for pupyMPI"""
    pass
    
class MPITopologyException(Exception): 
    """Custom exception for Topologies"""
    pass

class MPINoSuchRankException(MPIException):
    pass

class MPIInvalidTagException(MPIException):
    pass

class MPICommunicatorGroupNotSubsetOf(MPIException):
    pass