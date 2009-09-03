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
        return "<Group %s members: %s>" % (len(self.members), self.members)

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
        newlist = [p for p in self.members if p.rank in required_members]
        newGroup = Group()
        Logger().warn("Non-Implemented method 'group.incl' called.")
        
    def excl(self, excluded_members):
        """
        creates a group excluding listed members of an existing group
        """
        Logger().warn("Non-Implemented method 'group.excl' called.")
        
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