import sys, os, copy, signal, threading
from optparse import OptionParser
from mpi import constants
from mpi.network.utils import pickle
import socket, select
from mpi.network.utils import get_raw_message

from mpi.network import utils

class SendSimpleCommand(threading.Thread):

    def __init__(self, cmd_id, rank, hostinfo, timeout=None, pong=False):
        super(SendSimpleCommand, self).__init__()

        self.report = False
        self.report_data = ""
        self.finished = threading.Event()

        self.cmd_id = cmd_id
        self.rank = rank
        
        self.timeout = timeout
        self.pong = pong

        for participant in hostinfo:
            hostname, portno, rank, security_component = participant
            if rank == self.rank:
                self.hostname = hostname
                self.portno = portno
                self.security_component = security_component

    def wait_until_ready(self):
        self.finished.wait()
        return self.report, self.report_data

    def run(self, *args, **kwargs):
        try:
            connection = socket.create_connection( (self.hostname, self.portno), 4.0 )
            if not connection:
                self.report = "Could not connect to rank %d. We received a connect timeout" % self.rank
            else:
                # Send the message
                message = utils.prepare_message(self.security_component, -1, cmd=self.cmd_id, comm_id=-1)
                utils.robust_send(connection, message)

                # Test if we should also receive a message back from the rank. If so, we wait
                # for that message for a specific timeout. If we haven't received the message
                # by then, the command was not a sucess. Otherwise it was. 
                if self.pong:
                    incomming, _, errors = select.select([connection], [], [connection], self.timeout or 5)
                    if incomming:
                        # We read the message from the connection and set that as the result_data. 
                        rank, cmd, tag, ack, comm_id, data = get_raw_message(incomming[0])
                        
                        self.report = True
                        self.report_data = data
                    else:
                        self.report_data = "Connection timeout (30 seconds)"
                else:
                    self.report = True        
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