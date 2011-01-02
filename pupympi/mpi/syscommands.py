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
"""
syscommands.py - contains logic for handling system messages.
"""

# This is **very** important. The use of functools will
# keep the wrapped functions name and docstrings. If not
# here, the documentation will fall apart.
from functools import wraps
import sys

def find_mpi(obj):
    from mpi import MPI
    from mpi.communicator import Communicator

    if isinstance(obj, MPI):
        return obj
    elif isinstance(obj, Communicator):
        return obj.mpi
    else:
        print type(obj)

def handle_system_commands(f, *args, **kwargs):
    @wraps(f)
    def inner(self, *args, **kwargs):
        # Find MPI instance.
        mpi = find_mpi(self)

        # execute the system messages if there are any
        with mpi.pending_systems_commands_lock:
            execute_commands(mpi)

        return f(self, *args, **kwargs)
    return inner

from mpi import constants
def execute_commands(mpi):
    """
    Execute the actual system commands. This functions returns a
    boolean indicating if the decorated function should be called.
    """
    from mpi.network.utils import robust_send, prepare_message
    rest_list = []
    for obj in mpi.pending_systems_commands:
        cmd, connection, user_data = obj
        rank = mpi.MPI_COMM_WORLD.comm_group.rank()
        # Handle the message in a big if-statement. When / if the number
        # of commands escalades, we should consider moving them away.
        if cmd == constants.CMD_ABORT:
            sys.exit(1)

        elif cmd == constants.CMD_PING:
            # We need to access the rank like this. Calling rank() on the
            # communicator will active this function again. Should be
            # apply some locking?
            msg = prepare_message("PONG", rank)
            robust_send(connection, msg)

        elif cmd == constants.CMD_READ_REGISTER:
            # Send our registers. We just send everything and let the
            # client filter.
            msg = prepare_message(mpi.user_register, rank)
            robust_send(connection, msg)

        elif cmd == constants.CMD_MIGRATE_PACK:
            # This if is just here so people know it is not missing. We
            # handle this command in a different way.
            rest_list.append(obj)

    mpi.pending_systems_commands = rest_list

def availablity():
    """
    A function testing the system for command support. This function is
    called when the environment is started (as we know all the commands
    from the start).

    We simply hard code the first couple of avils as they should be there
    always. But wrapping it server side is a nicer way to handle everything
    at the mpirun-host.
    """
    avail_pack = True
    try:
        from mpi import dill
    except ImportError:
        avail_pack = False

    return {
        constants.CMD_ABORT : True,
        constants.CMD_PING : True,
        constants.CMD_MIGRATE_PACK : avail_pack,
        constants.CMD_READ_REGISTER : True,
    }

