#!/usr/bin/env python
# encoding: utf-8
"""
group.py - contains class definition for Group functionality.
"""

import sys
import os
import copy
import unittest
from mpi.logger import Logger
from mpi import constants
from mpi.exceptions import MPIException, MPINoSuchRankException, MPIInvalidRangeException, MPIInvalidStrideException


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
        return self.size() == 0

    def _global_ranks(self):
        """
        Convenience function to get set of members' global ranks
        """
        ranks = set()
        for k in self.members:
            ranks.add(self.members[k]['global_rank'])

        return ranks

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
        if self.members == other_group.members:            
            return constants.MPI_IDENT
        else:
            globRanksSelf = self._global_ranks()
            globRanksOther = other_group._global_ranks()
            if globRanksSelf == globRanksOther:
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
        o = other_group._global_keyed()
        translated = []
        for r in ranks:
            try:
                gRank = self.members[r]['global_rank']
            except KeyError, e:
                raise MPINoSuchRankException("Can not translate to rank %i since it is not in group"%r)
            
            try:
                # Found in the other group, now translate to that groups' local rank
                translated.append(o[gRank])
            except KeyError, e:
                # Unmatched in other group means not translatable
                translated.append(constants.MPI_UNDEFINED)
        
        return translated
        

    def union(self, second_group):
        """
        creates a group by union of two groups
        
        The rank ordering of the new group is based on rank ordering in the self
        group secondarily on ordering of second group
        """
        
        # If caller has rank in first group that rank is retained
        # Otherwise caller gets rank -1 and if caller has rank in second group
        # new rank is assigned in construction loop (rank remains -1 if caller is in neither group)
        my_rank = self.rank()
            
        second_rank = second_group.rank()
        
        #Get a set of world ranks from first group
        first_ranks = self._global_ranks()
        # Start with first group
        union_members = copy.copy(self.members)
        # Start ranking from highest rank+1
        next_rank = self.size()

        for k in second_group.members:
            gRank = second_group.members[k]['global_rank']
            # If already included we ignore
            if gRank in first_ranks:
                continue
            else:
                union_members[next_rank] = second_group.members[k] # Keep global rank etc.
                if k == second_rank: # Was it me?
                    my_rank = next_rank
                    
                next_rank += 1
        
        union_group = Group(my_rank)
        union_group.members = union_members
        return union_group
        
        
    def intersection(self, other_group):
        """
        creates a group from the intersection of two groups 
        
        The rank ordering of the new group is based on rank ordering in the self
        group        
        """
        next_rank = 0
        my_rank = -1 # Caller's rank in new group
        intersection_members = {}
        others = other_group._global_keyed()
        
        for k in self.members:
            gRank = self.members[k]['global_rank']
            try:
                # Does k global rank exist in other group?
                other_rank = others[gRank] # This raises ValueError if key not found
                intersection_members[next_rank] = self.members[k] # Keep global rank etc.
                if self.rank() == k:
                    my_rank = next_rank
                    
                next_rank += 1
            except KeyError, e:
                continue
        
        intersection_group = Group(my_rank)
        intersection_group.members = intersection_members
        return intersection_group
    
    def difference(self, other_group):
        """
        creates a group from the difference between two groups
        
        The group returned contains all members of the first groups that are not
        in the second group
        """
        next_rank = 0
        my_rank = -1 # Caller's rank in new group
        difference_members = {}
        others = other_group._global_keyed()
        
        for k in self.members:
            gRank = self.members[k]['global_rank']
            # Does k global rank exist in other group?
            if not gRank in others:
                # Since k is not in other group it is part of the difference
                difference_members[next_rank] = self.members[k] # Keep global rank etc.
                if self.rank() == k:
                    my_rank = next_rank                
                next_rank += 1
        
        difference_group = Group(my_rank)
        difference_group.members = difference_members
        return difference_group
    
    def incl(self, required_members):
        """
        creates a new group from members of an existing group
        required_members = list of ranks from existing group to include in new
        group, also determines the order in which they will rank in the new group
        """
        # No duplicate ranks allowed
        if len(set(required_members)) < len(required_members):
            raise MPIException("invalid call to incl, all ranks must be unique")
        
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
        # No duplicate ranks allowed
        if len(set(excluded_members)) < len(excluded_members):
            raise MPIException("invalid call to excl, all ranks must be unique")
            
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
    
    def range_incl(self, triples):
        """
        Produces a group by including ranges of processes from an existing group
        
        argument is a list of triples specifying (startrank,endrank,stride)
        the new group produced includes the list of ranks resulting from the
        evaluation of all triples
        
        NOTE: start and end are inclusive, that is
        range_incl([(42,42,1)])
        produces the group with rank 42
        
        Stride can be negative and startrank > endrank. So
        range_incl([(9,3,-2])
        produces the group with [9, 7, 5, 3] included
        """
        inclusions = []
        for (start,end,stride) in triples:
            if stride == 0:
                raise MPIInvalidStrideException("Illegal call to range_incl - stride can not be 0")
            
            # We want endrank to be included, so add or subtract one depending on stride
            if stride > 0:
                l = range(start,end+1, stride)
            else:
                l = range(start,end-1, stride)
            inclusions += l
        
        # Check for duplicates is done here instead of deferring to incl() to
        # provide better error message
        if len(set(inclusions)) < len(inclusions):
            raise MPIInvalidRangeException("Illegal call to range_incl - range contains duplicate ranks: %s " % (str(inclusions)))
            
        return self.incl(inclusions)

        
        

    def range_excl(self, triples):
        """
        Produces a group by excluding ranges of processes from an existing group
        
        argument is a list of triples specifying (startrank,endrank,stride)
        the new group produced excludes the list of ranks resulting from the
        evaluation of all triples
        
        NOTE: start and end are inclusive, that is
        range_excl([(42,42,1)])
        produces the same group with rank 42 excluded        
        """
        exclusions = []
        for (start,end,stride) in triples:
            if stride == 0:
                raise MPIInvalidStrideException("Illegal call to range_incl - stride can not be 0")
            
            # We want endrank to be excluded, so add or subtract one depending on stride
            if stride > 0:
                l = range(start,end+1, stride)
            else:
                l = range(start,end-1, stride)
            exclusions += l
        
        # Check for duplicates is done here instead of deferring to incl() to
        # provide better error message
        if len(set(exclusions)) < len(exclusions):
            raise MPIInvalidRangeException("Illegal call to range_excl - range contains duplicate ranks: %s " % (str(exclusions)))
            
        return self.excl(exclusions)
        
    def free(self):
        """
        Marks a group for deallocation
        """
        raise NotImplementedException("free targeted for version 1.1")
        return None
