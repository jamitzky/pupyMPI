#!/usr/bin/env python2.6
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
#
from utils import SendSimpleCommand, print_reports, parse_args
from mpi import constants
import sys

def main():
    ranks, hostinfo, bypass = parse_args()

    # Test if we have a "simple" command. That is, we can handle it by simply
    # sending a
    try:
        scmd_id = constants.CMD_ABORT

        # Start a thread for each rand we want to send the command to.
        threads = {}
        for rank in ranks:
            t = SendSimpleCommand(scmd_id, rank, hostinfo, bypass)
            threads[rank] = t
            t.start()

        reports = []
        for rank in threads:
            t = threads[rank]
            t.wait_until_ready()

            if t.error:
                reports.append("%d: %s" % (rank, t.error))
            else:
                reports.append("%d: Abort command sent!" % rank)

            t.join()

        print_reports(reports)
        sys.exit(0)

    except KeyError:
        pass

    parser.error("Can't find that command. Did you miss spell something?")

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    main()

