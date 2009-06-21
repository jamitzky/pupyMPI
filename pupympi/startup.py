#!/usr/bin/env python2.6


def hello_world(from_place):
    import mpi
    print "hello world. I'm %d of %d (calling from %s)" % (mpi.rank(), mpi.size(), from_place)

import mpi
mpi.initialize(15, hello_world, "berlin")

# blank
