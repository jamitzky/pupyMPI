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
from mpi import constants

class Group:
    """
    This class represents an MPI group. All operations are local.
    """
    def __init__(self, my_rank=None):
        self.members = {}
        if my_rank is None: # Used for creating empty group
            self.my_rank = -1
        else:
            self.my_rank = my_rank

    def __repr__(self):
        return "<Group: %s members: %s>" % (len(self.members), self.members)
        
    def _is_empty(self):
        """
        Convenience function to test if a group is empty
        """
        
        # TODO Still arguing over whether we should return MPI_GROUP_EMPTY as a singleton empty group instead
        return self.size() == 0

    def _global_ranks(self):
        """
        Convenience function to get list of members' global ranks
        """
        l = []
        for k in self.members:
            l.append(self.members[k]['global_rank'])

        return l

    def _global_keyed(self):
        """
        Convenience function to get dict of {global_rank:group_rank) for a group
        (that is the global rank as key with group rank as value)
        """
        d = {}
        for k in self.members:
            gRank = self.members[k]['global_rank']
            d[gRank] = k

        return d

    def size(self):
        """
        returns number of processes in group 
        """
        return len(self.members)

    def rank(self):
        return self.my_rank
        
    def compare(self, other_group):
        """
        Compares group members and group order.
        If the two groups have same members in same order MPI_IDENT is returned.
        If members are the same but order is different MPI_SIMILAR is returned.
        Otherwise MPI_UNEQUAL is returned.
        """
        if self == other_group:            
            return constants.MPI_IDENT
        else:
            globRanksSelf = self._global_ranks()
            globRanksOther = other_group._global_ranks()
            if set(globRanksSelf) == set(globRanksOther):
                return constants.MPI_SIMILAR
            else:
                return constants.MPI_UNEQUAL

    def translate_ranks(self, ranks, other_group):
        """
        translates ranks of processes in one group to those in another group
        
        Input:
        - A list of ranks to be translated to the
        corresponding ranks in the other group
        - The other group
        
        Output:
        - List of translated ranks/MPI_UNDEFINED if no translation existed
        
        """
        s = self._global_keyed()
        o = other_group._global_keyed()
        translated = []
        for r in ranks:
            # FIXME: This lookup should check for key error in case joe sixpack passes bad ranks
            # ... actually you are only allowed to pass valid ranks so throw an error?
            gr = self.members[r]['global_rank']
            
            try:
                # Found in the other group, now translate to that groups' local rank
                translated.append(o[gr])
            except ValueError, e:
                # Unmatched in other group means not translatable
                translated.append(constants.MPI_UNDEFINED)
        
        return translated
        
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
        creates a new group from members of an existing group
        required_members = list of ranks from existing group to include in new
        group, also determines the order in which they will rank in the new group
        """
        # TODO Incl/excl very simply implemented, could probably be more pythonic.
        #Logger().debug("Called group.incl (me %s), self.members = %s, required_members %s" % (self.rank(), self.members, required_members))
        new_members = {}
        new_rank = -1 # 'my' new rank
        counter = 0 # new rank for each process as they are added to new group
        
        for p in required_members:
            new_members[counter] = self.members[p]
            if p == self.rank():
                new_rank = counter
            counter += 1

        if counter is 0:
            #Logger().debug("Empty group created")
            return constants.MPI_GROUP_EMPTY
       
        new_group = Group(new_rank)
        new_group.members = new_members
        return new_group
        
    def excl(self, excluded_members):
        """
        creates a group excluding listed members of an existing group
        """
        #Logger().debug("Called group.excl (me %s), self.members = %s, excluded_members %s" % (self.rank(), self.members, excluded_members))
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
        
        if counter is 0:
            Logger().debug("Empty group created")
            return constants.MPI_GROUP_EMPTY

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