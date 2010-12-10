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
            hostname, portno, rank, security_component = participant
            if rank == self.rank:
                self.hostname = hostname
                self.portno = portno
                self.security_component = security_component

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
                message = utils.prepare_message(self.security_component, -1, cmd=self.cmd_id, comm_id=-1)
                utils.robust_send(connection, message)

                self.report = "abort message successful sent to %d" % self.rank

        except Exception, e:
            self.report = "Error in connecting to rank %d: %s" % (self.rank, str(e))

        self.finished.set()

def parse_args():
    def parse_handle(filename):
        return pickle.load(open(filename, "rb"))

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

    options, args = parser.parse_args()
    handle = args[0]
    err = False

    try:
        hostinfo = parse_handle(handle)
    except:
        parser.error("Cant parse the handle file")

    try:
        ranks = get_ranks(options.ranks, hostinfo)
    except Exception, e:
        parser.error("Invalid ranks")

    return ranks, hostinfo

def print_reports(reports):
    for r in reports:
        print r