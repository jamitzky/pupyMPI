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
import sys, os, copy, signal, threading
from optparse import OptionParser
from mpi import constants
from mpi.network.utils import pickle
import socket

from mpi.network import utils

class SendSimpleCommand(threading.Thread):

    def __init__(self, cmd_id, rank, hostinfo):
        super(SendSimpleCommand, self).__init__()

        self.report = None
        self.finished = threading.Event()

        self.cmd_id = cmd_id
        self.rank = rank

        for participant in hostinfo:
            hostname, portno, rank = participant
            if rank == self.rank:
                self.hostname = hostname
                self.portno = portno

    def wait_until_ready(self):
        self.finished.wait()
        return self.report

    def run(self, *args, **kwargs):
        try:
            connection = socket.create_connection( (self.hostname, self.portno), 4.0 )
            if not connection:
                self.report = "Could not connect to rank %d. Timeout" % self.rank
            else:
                # Send the message
                message = utils.prepare_message(None, -1, cmd=self.cmd_id, comm_id=-1)
                utils.robust_send(connection, message)

                self.report = "abort message successful sent to %d" % self.rank

        except Exception, e:
            self.report = "Error in connecting to rank %d: %s" % (self.rank, str(e))

        self.finished.set()

def parse_args():
    def parse_handle(filename):
        return pickle.load(open(filename))

    def get_ranks(ranks, hostinfo):
        all_ranks = [h[2] for h in hostinfo]
        final_ranks = None
        if ranks:
            ranks = ranks.split(",")
            ranks = list(set(map(int, ranks)))

            if max(ranks) > max(all_ranks) or min(ranks) < min(all_ranks):
                raise Exception("Invalid ranks")
        else:
            ranks = all_ranks

        ranks.sort()
        return ranks

    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="pupysh version %s" % (constants.PUPYVERSION))

    parser.add_option("-r", "--ranks", dest="ranks", help="A comma sep list of ranks this command should be executed on")
    parser.add_option("-f", "--handle", dest="handle", help="The path to the file handle containing process information")

    options, args = parser.parse_args()
    err = False

    # Simply arguments.
    if args is None or len(args) == 2:
        parser.error("You need to specify a positional argument: the command to run.")

    try:
        hostinfo = parse_handle(options.handle)
    except:
        parser.error("Cant parse the handle file")

    try:
        ranks = get_ranks(options.ranks, hostinfo)
    except Exception, e:
        parser.error("Invalid ranks")

    command = args[0].lower()

    return command, ranks, hostinfo

def print_reports(reports):
    for r in reports:
        print r

def main():
    command, ranks, hostinfo = parse_args()

    # variable setup
    simple_commands = {
        'abort' : constants.CMD_ABORT,
    }

    # Test if we have a "simple" command. That is, we can handle it by simply
    # sending a
    try:
        scmd_id = simple_commands[command]

        # Start a thread for each rand we want to send the command to.
        threads = []
        for rank in ranks:
            t = SendSimpleCommand(scmd_id, rank, hostinfo)
            t.start()
            threads.append(t)

        reports = []
        for t in threads:
            report = t.wait_until_ready()
            reports.append(report)
            t.join()

        print_reports(reports)
        sys.exit(0)

    except KeyError:
        pass

    parser.error("Can't find that command. Did you miss spell something?")

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    main()

