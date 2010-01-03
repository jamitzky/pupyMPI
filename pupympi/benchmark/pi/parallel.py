#!/usr/bin/env python

import math, random, sys, time
from mpi import MPI
from mpi import constants

num_in = 0
total = 0

# MPI setup
mpi = MPI()
comm = mpi.MPI_COMM_WORLD
rank = comm.rank()
size = comm.size()

comm.barrier()

# regular setup
if ( len(sys.argv) != 2 ):
    print "Usage: " + sys.argv[0] + " sample_number"
    mpi.finalize()
    sys.exit(0)
    
max_cmdline = int(sys.argv[1]) 
max = max_cmdline / size

t1 = time.time()

# algorithm
random.seed()
for i in xrange(max):
 x = random.uniform(0,1)
 y = random.uniform(0,1)
 if x*x + y*y <= 1:
  num_in += 1
 total += 1

# distribute

total = max_cmdline
print "Rank %s: total is %s, num_in is %s, time %s" % (rank, total, num_in, time.time()-t1)
num_in_list = comm.gather(num_in)

# rank 0 gathers and displays
if rank == 0:
    summed_num_in = sum(num_in_list)
    #print "total is %s, summed_num_in is %s" % (rank, total, summed_num_in)
    ratio = float(summed_num_in) / float(total)
    my_pi = 4 * ratio

    print "Within circle: " + str(summed_num_in)
    print "Total: " + str(total)
    print "Ratio: " + str(ratio)
    print "Python's Internal Pi: " + str(math.pi)
    print "*** Approx. Pi: " + str(my_pi) + " ***"
    print "Discrepancy: " + str(math.pi - my_pi)
    print "Internal time: " + str(time.time() - t1)

mpi.finalize()