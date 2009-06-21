#!/usr/bin/env python2.6

import mpi

def hello_world(from_place, test="hej"):
    print "hello world. I'm %d of %d (calling from %s)" % (mpi.rank(), mpi.size(), from_place)

    # blank
    mpi.finalize()

mpi.initialize(15, hello_world, "berlin", test="hej")

