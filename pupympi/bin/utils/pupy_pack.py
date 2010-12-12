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
from utils import parse_args, avail_or_error
from mpi import constants
from mpi.network.utils import create_random_socket
from mpi.logger import Logger
import sys, dill, select, socket

def main():
    Logger("migrate.log", "migrate", True, True, True)

    ranks, hostinfo, bypass = parse_args()

    # Create a socket we can receive results from.
    sock, hostname, port_no = create_random_socket()

    sock.listen(len(ranks))

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
            print "connection timeout for rank", rank
            sys.exit(1)

        from mpi.network import utils as mpi_utils

        message = mpi_utils.prepare_message(data, -1, cmd=constants.CMD_MIGRATE_PACK)
        mpi_utils.robust_send(connection, message)

    all_data = {}

    # Receive the messages back from each of the ranks.
    for _ in range(len(ranks)):
        connection, _ = sock.accept()

        incomming, _, errors = select.select([connection], [], [connection], 5)
        if incomming:
            rank, cmd, tag, ack, comm_id, data = mpi_utils.get_raw_message(incomming[0])
            connection.close()
            all_data[rank] = dill.loads(data)
        else:
            print "Connection read timeout"

    # Write the final data to a file
    import tempfile
    _, filename = tempfile.mkstemp(prefix="pupy")

    fh = open(filename, "wb")
    dill.dump(all_data, fh)

    fh.close()
    print "The processes is now packed into a file: %s" % filename

    sys.exit(0)

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    main()

