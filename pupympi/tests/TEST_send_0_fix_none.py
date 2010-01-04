#!/usr/bin/env python2.6
# meta-description: Test that "", [] () and 0 all result in None when sent
# meta-expectedresult: 0
# meta-minprocesses: 10

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

        if c != c_received:
            match = False
            print "-"*80
            print "Received", c_received
            print "Expected", c
            print "-"*80,"\n"

assert match


# Close the sockets down nicely
mpi.finalize()
