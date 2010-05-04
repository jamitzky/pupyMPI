#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#

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
    Raised in calls when specifying a rank in a communicator that is not a
    member of the communicator.
    """
    pass

class MPIInvalidRankException(MPIException):
    """
    Raised in calls where an invalid rank is supplied. Remember all ranks should
    be positive integers.
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
    Raised in calls where an invalid tag is supplied. Remember all
    tags should be integers. See also the section about :ref:`TagRules`. 
    """
    pass

class MPICommunicatorGroupNotSubsetOf(MPIException):
    """
    Raised when a new communicator is created from a group that is not a subset
    of the parent communicator group.
    """
    pass
    
class MPICommunicatorNoNewIdAvailable(MPIException):
    """
    Raised if it is no longer possible to create new communicators because there
    are no unique identifiers available. This typically happens when
    communicators are created locally since only 31 can be created in total. 
    """
    pass
