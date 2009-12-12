#!/usr/bin/env python2.6

import sys
import pstats


profileFile = sys.argv[1]

p = pstats.Stats(profileFile)

p.strip_dirs() # Remove superflous directory paths

#p.sort_stats('time').print_stats(10)
p.sort_stats('cum', 'time')
p.print_callers(200)


