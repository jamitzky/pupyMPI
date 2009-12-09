#!/usr/bin/env python2.6

import pstats
p = pstats.Stats('/home/fred/Diku/ppmpi/code/pupympi/logs/pupympi.profiling.rank0') # old name of file
p.strip_dirs()
#p.sort_stats('time').print_stats(10)
p.sort_stats('cum', 'time')
p.print_callers(20)
