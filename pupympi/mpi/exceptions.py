#!/usr/bin/env python
# encoding: utf-8

# Define exception class
class MPIException(Exception): 
    """
    General exception for pupyMPI. Look into the API at the
    specific function for the actual cause of this exception. 
    """
    pass
    
class MPITopologyException(MPIException): 
    """
    Custom exception for Topologies
    """
    pass

class MPINoSuchRankException(MPIException):
    """
    Raised in calls where an invalid rank i supplied. 
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
    Raised in calls where an invalid tag i supplied. Remember all
    tags should be integers. See also the section about :ref:`TagRules`. 
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
