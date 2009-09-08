#!/usr/bin/env python
# encoding: utf-8
"""
group.py

Created by Jan Wiberg on 2009-09-01.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import unittest
from mpi.logger import Logger


class Group:
    """
    This class represents an MPI group. All operations are local.
    """
    def __init__(self, my_rank):
        self.members = []
        self.my_rank = my_rank
        
    def __repr__(self):
        return "<Group: %s members: %s>" % (len(self.members), self.members)
        
    def is_empty(self):
        # TODO Still arguing over whether we should return MPI_GROUP_EMPTY as a singleton empty group instead
        return size() == 0

    def size(self):
        """
        returns number of processes in group 
        """
        return len(self.members)

    def rank(self):
        return self.my_rank
        
    def compare(self, other_group):
        """
        compares group members and group order 
        """
        Logger().warn("Non-Implemented method 'group.compare' called.")

    def translate_ranks(self, other_group):
        """
        translates ranks of processes in one group to those in another group
        """
        Logger().warn("Non-Implemented method 'group.translate_ranks' called.")
        
    def union(self, other_group):
        """
        creates a group by combining two groups 
        """
        Logger().warn("Non-Implemented method 'group.union' called.")
        
    def intersection(self, other_group):
        """
        creates a group from the intersection of two groups 
        """
        Logger().warn("Non-Implemented method 'group.intersection' called.")
        
    def difference(self, other_group):
        """
        creates a group from the difference between two groups
        """
        Logger().warn("Non-Implemented method 'group.difference' called.")
        
    def incl(self, required_members):
        """
        creates a group from listed members of an existing group
        required_members = list of new members
        """
        # TODO Incl/excl very simply implemented, could probably be more pythonic.
        Logger().debug("Called group.incl (me %s), self.members = %s, required_members %s" % (self.rank(), self.members, required_members))
        new_members = {}
        new_rank = -1 # 'my' new rank
        counter = 0 # new rank for each process as they are added to new group
        
        for p in required_members:                
            new_members[counter] = self.members[p]
            if p == self.rank():
                new_rank = counter
            counter += 1
        
        # its allowed not to be a member of the group
        # if new_rank is -1:
        #            return None
       
        new_group = Group(new_rank)
        new_group.members = new_members
        return new_group
        
    def excl(self, excluded_members):
        """
        creates a group excluding listed members of an existing group
        """
        Logger().debug("Called group.excl (me %s), self.members = %s, excluded_members %s" % (self.rank(), self.members, excluded_members))
        new_members = {}
        new_rank = -1 # 'my' new rank
        counter = 0 # new rank for each process as they are added to new group
        for p in self.members:
            if p in excluded_members:
                continue
                
            new_members[counter] = self.members[p]
            if p == self.rank():
                new_rank = counter
            counter += 1
        
        # its allowed not to be a member of the group
        # if new_rank is -1:
        #            return None

        new_group = Group(new_rank)
        new_group.members = new_members
        return new_group        
    def range_incl(self, arg):
        # FIXME decide if to implement
        pass

    def range_excl(self, arg):
        # FIXME decide if to implement
        pass
        
    def free(self):
        """
        Marks a group for deallocation
        """
        # FIXME decide if to implement
        pass

class groupTests(unittest.TestCase):
    def setUp(self):
        pass


if __name__ == '__main__':
    unittest.main()