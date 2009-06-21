#!/usr/bin/env python2.6

import mpi

def hello_world():
    rank = mpi.rank()
    
    if rank == 1:
        handle = mpi.isend(0, "Dette er en test", 0)
        mpi.wait(handle)
    elif rank == 0:
        #handle = mpi.irecv(1, 0)
        #data = mpi.wait(handle)
        pass
        #print "Vi har modtaget fra 1: ", data
        
def isend(destination, content, tag, comm=None):
    # blank
    mpi.finalize()

mpi.initialize(2, hello_world)

