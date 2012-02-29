#!/usr/bin/env python
#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
#
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.

from utils import SendSimpleCommand, print_reports, parse_extended_args, get_standard_parser
from mpi import constants
import sys

def main():
    # Build the standard parser object with bypass, rank information etc. 
    parser = get_standard_parser()
    
    # Extend the parser with special config parameters etc.
    parser.add_option("-c", "--config", dest="data", action="append", help="Use this parameter to change a setting. For example: -c MYSETTING=MYVALUE")
    
    # Use the parser and return all the parsed args.
    options, args = parse_extended_args(parser)
    
    
    ranks = options.ranks
    hostinfo = options.hostinfo
    bypass = options.bypass
    
    if not options.data:
        parser.error("No settings entered. ")
    
    data = {}
    for c in options.data:
        ele = c.split("=")
        if len(ele) != 2:
            parser.error("Cant parse the settings. You need to set a KEY=VAL after the -c")
        else:
            key, val= ele
            data[key.upper()] = val

    try:
        scmd_id = constants.CMD_CONFIG

        # Start a thread for each rand we want to send the command to.
        threads = {}
        for rank in ranks:
            t = SendSimpleCommand(scmd_id, rank, hostinfo, bypass, pong=True, timeout=30, data=data)
            t.start()
            threads[rank] = t

        reports = []
        for rank in threads:
            t = threads[rank]
            t.wait_until_ready()
            if t.error:
                reports.append("%d: %s" % (rank, t.error))
            else:
                ljuster = 0
                for key in t.data:
                    ljuster = max(len(key), ljuster)
                
                
                headline = "=" * 40 + " rank:" +  str(rank) +  "="*40
                print headline
                
                for key in t.data:
                    print "\t" + key.ljust(ljuster) + ": " + t.data[key][1]
                
                print "="*len(headline)
                print ""
                
            t.join()

        print_reports(reports)

        sys.exit(0)

    except KeyError:
        pass

    parser.error("Can't find that command. Did you miss spell something?")

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    main()

