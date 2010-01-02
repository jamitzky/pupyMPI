"""
The constants module contains a number of predefined tags, sources and other 
structures either useable as arguments in MPI functions or returned from 
MPI functions.
"""

import os

# Auxillary tags
# TODO: This is a nasty way of going to dirs up and down into logs. There must be a prettier way
#       Maybe we shouldn't be afraid of changing current working directory
LOGDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/logs/"

# Predefined tags
MPI_TAG_ANY = -1 # public, this and below
"""
MPI_TAG_ANY is a special tag matching any other tag - a wildcard if you will.
This is also the default tag used if you do not specify a particular tag.
You can use this if you don't want to filter the incoming message on a specific tag. 
"""

MPI_SOURCE_ANY = -2 # to be recognizable
"""
MPI_SOURCE_ANY is a special rank matching any rank - a wildcard like the any-tag.
This is also the default rank used if you do not specify a particular rank.
You can use this if you don't want to filter the incoming message on sender rank.
"""

# Other constants. NOTE: These are advisory only
MPI_COMM_NULL = None
"""
MPI_COMM_NULL represents the empty communicator. You shouldn't normally see this
unless you tried to create a communicator with conditions resulting in it being
empty.
"""

# internal tags below. 
TAG_ACK     = -3 
TAG_BCAST   = -4 
TAG_EMPTY   = -5
TAG_BARRIER = -6
TAG_COMM_CREATE = -7
TAG_ALLREDUCE = -8
TAG_REDUCE = -9
TAG_INITIALIZING = -10
TAG_FULL_NETWORK = -11 
TAG_ALLTOALL = -12
TAG_SCATTER = -13
TAG_ALLGATHER = -14
TAG_GATHER = -15
TAG_SCAN = -16
TAG_SHUTDOWN = -17

# NOT IMPLEMENTED:
# MPI_COMM_SELF (MPI 2.x)

MPI_GROUP_EMPTY = None # gets set later on an empty group to avoid cyclic imports
"""
MPI_GROUP_EMPTY represents the empty group. You shouldn't normally see this
unless you tried to create a group with conditions resulting in it being
empty.
"""

MPI_IDENT       = 0     # Identical 
"""
Jan, document me
"""
MPI_CONGRUENT   = 0     # (only for MPI_COMM_COMPARE) The groups are identical 
"""
Jan, document me
"""
MPI_SIMILAR     = 1     # Same members, but in a different order 
"""
Jan, document me
"""
MPI_UNEQUAL     = -1    # Different
"""
Jan, document me
"""
MPI_UNDEFINED   = -3    # Like SGI's MPI (http://scv.bu.edu/documentation/tutorials/MPI/alliance/communicators/MPI_Group_rank.html)
"""
Jan, document me
"""

JOB_INITIALIZING = -1

# commands used for indicating is this is a system
# message.
CMD_USER = 0
CMD_ABORT = 1
CMD_SYSTEM = 2
