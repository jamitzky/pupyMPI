#!/usr/bin/env python
"""
sequential.py

basic sequential Python version of Monte Carlo Pi approximator
"""
import math, random, sys

num_in = 0
total = 0

if ( len(sys.argv) != 2 ):
 print "Usage: " + sys.argv[0] + " sample_number"
 sys.exit(1)
max = int(sys.argv[1])

random.seed()
for i in xrange(max):
 x = random.uniform(0,1)
 y = random.uniform(0,1)
 if x*x + y*y <= 1:
  num_in += 1
 total += 1

ratio = float(num_in) / float(total)
my_pi = 4 * ratio

print "Within circle: " + str(num_in)
print "Total: " + str(total)
print "Ratio: " + str(ratio)
print "Python's Internal Pi: " + str(math.pi)
print "*** Approx. Pi: " + str(my_pi) + " ***"
print "Discrepancy: " + str(math.pi - my_pi)
