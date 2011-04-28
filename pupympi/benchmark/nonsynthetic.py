#!/usr/bin/env python
# encoding: utf-8
"""
nonsynthetic.py - collection of nonsynthetic tests
"""

import comm_info as ci

meta_has_meta = True
meta_processes_required = 1
meta_enlist_all = True
# This configuration is just for SOR for now
meta_schedule = {
    24: 1,
    64: 1,
}
#
#meta_schedule = {
#    24: 1,
#    64: 1,
#    128: 1,
#    512: 1,
#    1024: 1,
#    2048: 1,
#    4096: 1,
#}

def test_SOR(size, max_iterations):
    import sor.parallel
    import copy

    ### Setup parameters

    #Default problem size
    xsize=size
    ysize=size
    #xsize=24
    #ysize=24

    useGraphics=False

    epsilonFactor = 0.1

    update_freq = 0
    useGraphics = 0

    rank = ci.communicator.rank()
    world_size = ci.communicator.size()

    ci.synchronize_processes()

    t1 = ci.clock_function()

    (local_state, global_state, rboffset, epsilon) = sor.parallel.setup_problem(rank, world_size, xsize, ysize,epsilonFactor)

    # odd number of rows and odd rank means local state starts with a black point instead of red
    rboffset = (rank % 2) * (ysize % 2)

    #Start solving the heat equation
    sor.parallel.solve(rank, world_size, local_state, rboffset, epsilon, update_freq, useGraphics, ci.communicator)

    t2 = ci.clock_function()

    time = t2 - t1

    return time


def test_MCPi(size, max_iterations):
    import pi.parallel

    ### Setup parameters

    #Problem size of mc pi scales differently
    problemsize = size *1000

    useGraphics=False

    epsilonFactor = 0.1

    update_freq = 0
    useGraphics = 0

    rank = ci.communicator.rank()
    world_size = ci.communicator.size()

    t1 = ci.clock_function()

    ci.synchronize_processes()

    hits = pi.parallel.approximate(rank,problemsize)

    # distribute
    global_hits = ci.communicator.reduce(hits,sum)

    t2 = ci.clock_function()

    time = t2 - t1

    return time
