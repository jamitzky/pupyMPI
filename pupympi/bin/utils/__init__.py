import sys, os, copy, signal, threading
from optparse import OptionParser
from mpi import constants
from mpi.network.utils import pickle
import socket, select
from mpi.network.utils import get_raw_message

from mpi.network import utils

class SendSimpleCommand(threading.Thread):

    def __init__(self, cmd_id, rank, hostinfo, bypass=False, timeout=None, pong=False, data=None):
        super(SendSimpleCommand, self).__init__()

        self.data = None
        self.finished = threading.Event()

        self.cmd_id = cmd_id
        self.rank = rank

        self.timeout = timeout
        self.pong = pong
        self.error = ""
        self.send_data = data

        for participant in hostinfo:
            hostname, portno, rank, security_component, avail = participant
            if rank == self.rank:
                self.hostname = hostname
                self.portno = portno
                self.security_component = security_component

                self.do_run = True
                if not bypass:
                    try:
                        self.do_run = avail[cmd_id]
                    except KeyError:
                        print "Can not determine if the command can be executed. Playing it safe and will not execute anything. Use --bypass-avail-check (-b) if you want to force the command through"
                        self.do_run = False

    def wait_until_ready(self):
        self.finished.wait()

    def run(self, *args, **kwargs):
        if not self.do_run:
            self.finished.set()
            self.data = "Cancelled due to availablity check on the remote host"
            return

        try:
            connection = socket.create_connection( (self.hostname, self.portno), 4.0 )
            if not connection:
                self.error = "Could not connect to rank %d. We received a connect timeout" % self.rank
            else:
                # Send the message
                header,payload = utils.prepare_message((self.security_component, self.send_data), -1, cmd=self.cmd_id, comm_id=-1)
                utils.robust_send(connection, header+payload)

                # Test if we should also receive a message back from the rank. If so, we wait
                # for that message for a specific timeout. If we haven't received the message
                # by then, the command was not a sucess. Otherwise it was.
                if self.pong:
                    incomming, _, errors = select.select([connection], [], [connection], self.timeout or 5)
                    if incomming:
                        # We read the message from the connection and set that as the result_data.
                        rank, cmd, tag, ack, comm_id, _, data = get_raw_message(incomming[0])
                        data = pickle.loads(data)

                        self.data = data
                    else:
                        self.error = "Connection timeout (30 seconds)"
        except Exception, e:
            self.error = "Error in connecting to rank %d: %s" % (self.rank, str(e))

        self.finished.set()

def get_standard_parser():
    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="pupysh version %s" % (constants.PUPYVERSION))

    parser.add_option("-r", "--ranks", dest="ranks", help="A comma sep list of ranks this command should be executed on")
    parser.add_option("-b", "--bypass-avail-check", dest="bypass", action="store_true", default=False)
    return parser

def parse_extended_args(parser=None):
    def parse_handle(filename):
        obj = pickle.load(open(filename, "rb"))

        all_procs = obj['procs']
        args = obj['args']

        return all_procs, args

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

    if not parser:
        parser = get_standard_parser()

    options, args = parser.parse_args()
    handle = args[0]

    try:
        hostinfo, mpirun_args = parse_handle(handle)
        options.hostinfo = hostinfo
        options.mpirun_args = mpirun_args
    except:
        parser.error("Cant parse the handle file")

    try:
        options.ranks = get_ranks(options.ranks, options.hostinfo)
    except Exception, e:
        parser.error("Invalid ranks")

    return options, args

def parse_args(parser=None):
    options, args = parse_extended_args(parser=parser)
    return options.ranks, options.hostinfo, options.bypass

def avail_or_error(avail, rank, cmd):
    succ = True
    try:
        succ = avail[cmd]
    except:
        succ = False

    if not succ:
        print "This command is not avaiable on the host with rank %d" % rank

    return succ

def print_reports(reports):
    for r in reports:
        print r
