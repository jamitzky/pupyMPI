#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
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
"""
Operations for collective requests. These will take a
list and do something and return the result. There are
a number of settings you can set on the function itself
that will control the behaviour.

It's very easy to write custom operations as described :ref:`here <operations-api-label>`
"""

def MPI_sum(input_list):
    return sum(input_list)
MPI_sum.partial_data = True

def MPI_prod(input_list):
    """
    Multiplies all the elements. The elements must be
    integers, float etc. As an example the following code
    uses allreduce to calculate the factorial function of n,
    where n is the size of the world communicator.::

        from mpi import MPI
        from mpi.operations import MPI_prod

        mpi = MPI()

        # We start n processes, and try to calculate n!
        rank = mpi.MPI_COMM_WORLD.rank()
        fact = mpi.MPI_COMM_WORLD.allreduce(rank, prod)

        print "I'm rank %d and I also got the result %d. So cool" % (rank, fact)

        mpi.finalize()
    """
    p = 1

    # The input list is a list of dictionaries. We're only interested in
    # looking through the actual values.

    for e in input_list:
        p *= e
    return p

MPI_prod.partial_data = True

def MPI_max(input_list):
    """
    Returns the largest element in the list. The input can be any kind of list
    or pseudo list (string, tuple, array etc.).

    """
    #if isinstance(input_list[0], list):
    #    return max(max(input_list))
    #else:
    #    return max(input_list)
    return max(input_list)

MPI_max.partial_data = True

def MPI_min(input_list):
    """
    Returns the minimum element in the list.
    """
    return min(input_list)
MPI_min.partial_data = True

def MPI_avg(input_list):
    """
    Return the average of the elements
    """
    return sum(input_list)/len(input_list)