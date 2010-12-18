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
from utils import SendSimpleCommand, get_standard_parser, parse_extended_args
from mpi import constants
import sys

def main():
    # Get the standard parser and add some arguments to it.
    parser = get_standard_parser()

    parser.add_option("-k", "--keys=", dest="keys")

    options, args = parse_extended_args(parser=parser)

    keys = []
    try:
        if options.keys:
            keys = options.keys.split(",")
            keys = [s.strip() for s in keys]
    except Exception as e:
        parser.error("Can't handle the supplied keys. Error was: %s" % str(e))


    # Test if we have a "simple" command. That is, we can handle it by simply
    # sending a
    try:
        scmd_id = constants.CMD_READ_REGISTER

        # Start a thread for each rand we want to send the command to.
        threads = {}
        for rank in options.ranks:
            t = SendSimpleCommand(scmd_id, rank, options.hostinfo, options.bypass, pong=True, timeout=30)
            t.start()
            threads[rank] = t

        reports = {}
        for rank in threads:
            t = threads[rank]
            t.wait_until_ready()

            if t.error:
                reports[rank] = t.error
            else:
                reports[rank] = t.data
            t.join()

        for rank in reports:
            print "---------------- Registers for rank %d -------------------" % rank

            # Check for single strings (ie. errors)
            rank_data = reports[rank]
            if type(rank_data) == str:
                print rank_data
            else:
                for key in rank_data:
                    if (not keys) or key in keys:
                        d = reports[rank][key]
                        print "%s: %s" % (key, d)

            print "----------------------------------------------------------"
            print ""

        sys.exit(0)

    except KeyError:
        pass

    parser.error("Can't find that command. Did you miss spell something?")

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    main()

