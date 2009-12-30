#!/usr/bin/env python
# encoding: utf-8

# Define exception class
class MPIException(Exception): 
    """
    Custom exception for pupyMPI
    """
    pass
    
class MPITopologyException(MPIException): 
    """
    Custom exception for Topologies
    """
    pass

class MPINoSuchRankException(MPIException):
    """
    Document me
    """
    pass

class MPIInvalidStrideException(MPIException):
    """
    Custom exception for group (range) calls
    """
    pass

class MPIInvalidRangeException(MPIException):
    """
    Custom exception for group (range) calls
    """
    pass

class MPIInvalidTagException(MPIException):
    """
    Document me
    """
    pass

class MPICommunicatorGroupNotSubsetOf(MPIException):
    """
    Document me
    """
    pass
    
class MPICommunicatorNoNewIdAvailable(MPIException):
    """
    Document me
    """
    pass
