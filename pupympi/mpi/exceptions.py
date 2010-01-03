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
    Raised when a new communicator is created from a group that is not a subset of the parent communicator group.
    """
    pass
    
class MPICommunicatorNoNewIdAvailable(MPIException):
    """
    Raised if it is no longer possible to create new communicators because there are no unique identifiers available. This typically happens when communicators are created locally since only 31 can be created in total. 
    """
    pass
