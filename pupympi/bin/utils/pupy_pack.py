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
from utils import parse_extended_args, avail_or_error
from mpi import constants
from mpi.network.utils import create_random_socket
from mpi.logger import Logger
import sys, dill, select, socket
from threading import Thread, Event

class Receiver(Thread):
    def __init__(self, server_sock, no_procs, all_data):
        Thread.__init__(self)

        self.server_sock = server_sock
        self.no_procs = no_procs
        self.all_data = all_data

        self.connections = []

        self.done_event = Event()

    def run(self, *args, **kwargs):
        while not self.done_event.is_set():
            try:
                connection, _ = self.server_sock.accept()
                self.connections.append(connection)
            except:
                pass

            # Run through the connections and receive unhandled messages.
            incomming, _, errors = select.select(self.connections, [], self.connections, 5)
            if incomming:
                for connection in incomming:
                    from mpi.network import utils as mpi_utils
                    rank, cmd, tag, ack, comm_id, data = mpi_utils.get_raw_message(connection)
                    connection.close()

                    self.connections.remove(connection)

                    # An important note. We send this as a string. This way there is no reason
                    # for mpirun.py to unpickle it and then pickle it again.
                    self.all_data['procs'][rank] = data
                    print "Received for rank", rank

            # Test if we are done.
            print "no_procs", self.no_procs
            print "procs recv", len(self.all_data['procs'].values())
            if self.no_procs == len(self.all_data['procs'].values()):
                self.done_event.set()

    def wait(self):
        return self.done_event.wait()

def main():
    Logger("migrate", "migrate", True, True, True)

    options, args = parse_extended_args()

    ranks = options.ranks
    hostinfo = options.hostinfo
    bypass = options.bypass

    # Create a socket we can receive results from.
    sock, hostname, port_no = create_random_socket()
    sock.listen(len(ranks))

    all_data = {
        'procs' : {},
        'mpirun_args' : options.mpirun_args,
    }

    # Start a tread for reaciing.
    receiver = Receiver(sock, len(ranks), all_data)
    receiver.start()

    for participant in hostinfo:
        remote_host, remote_port, rank, security_component, avail = participant

        succ = True
        if not bypass:
            succ = avail_or_error(avail, rank, constants.CMD_MIGRATE_PACK)

        if not succ:
            sys.exit(1)

        # Data to send is a tuple with the security component, and then
        # command specific data
        data = (security_component, (hostname, port_no))
        connection = socket.create_connection( (remote_host, remote_port), 4.0 )
        if not connection:
            sys.exit(1)

        from mpi.network import utils as mpi_utils
        message = mpi_utils.prepare_message(data, -1, cmd=constants.CMD_MIGRATE_PACK)
        mpi_utils.robust_send(connection, message)

    # Wait until everybody sent back.
    receiver.wait()
    receiver.join()

    # Write the final data to a file
    import tempfile
    _, filename = tempfile.mkstemp(prefix="pupy")

    fh = open(filename, "wb")
    dill.dump(all_data, fh)

    fh.close()

    print "Halted system saved to file: ", filename

    sys.exit(0)

if __name__ == "__main__":
    main()

