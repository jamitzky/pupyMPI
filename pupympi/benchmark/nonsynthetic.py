#!/usr/bin/env python
# encoding: utf-8
"""
nonsynthetic.py - collection of nonsynthetic tests
"""

import comm_info as ci

meta_has_meta = True
meta_processes_required = 1
meta_enlist_all = True
meta_result_configuration = "special"
meta_schedule = {
    50: 10,
    100: 8,
    250: 5,
    500: 2,
    1000: 1,
    2000: 1,
}

def test_SOR(size, max_iterations):
    import sor.parallel
    import copy
   
    ci.synchronize_processes()

    (problem, rboffset) = sor.parallel.setup(ci.communicator, size, size, 0)

    t1 = ci.clock_function()

    for n in range(0, max_iterations):
        sor.parallel.solve(ci.communicator, copy.deepcopy(problem), rboffset)

    t2 = ci.clock_function()

    time = t2 - t1

    return time

