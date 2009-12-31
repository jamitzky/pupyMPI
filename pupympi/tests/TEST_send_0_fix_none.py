#!/usr/bin/env python2.6

# Simple pupympi program to test basic blocking send to blocking recieve
# This test is meant to be run with only two processes

# rank 0 sends message to rank 1 
from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

possible_none_content = ["", [], (), 0]
match = True

if rank == 0:
    for c in possible_none_content:
        world.send(1, c)
elif rank == 1: 
    for c in possible_none_content:
        c_received = world.recv(0)

        print "-"*80
        print "Received", c_received
        print "Expected", c
        print "-"*80,"\n"

        if c != c_received:
            match = False

assert match


# Close the sockets down nicely
mpi.finalize()
