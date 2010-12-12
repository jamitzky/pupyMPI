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

def handle_system_commands(f, *args, **kwargs):
    @wraps(f)
    def inner(self, *args, **kwargs):
        # Find the MPI instance by looking at self.
        # inner logic.
        from mpi import MPI
        from mpi.communicator import Communicator
        mpi = None
        if isinstance(self, MPI):
            mpi = self
        elif isinstance(self, Communicator):
            mpi = self.mpi
        else:
            Logger().warning("Can't find MPI instance when checking system messages. Looking at an object of type: %s" % type(self))

        # execute the system messages if there are any
        run_inner_func = True
        with mpi.pending_systems_commands_lock:
            if mpi.pending_systems_commands:
                run_inner_func = execute_commands(mpi, (f, args, kwargs))

        # calling the original function
        if run_inner_func:
            return f(self, *args, **kwargs)
    return inner

def execute_commands(mpi, bypassed):
    """
    Execute the actual system commands. This functions returns a
    boolean indicating if the decorated function should be called.
    """
    from mpi import constants
    from mpi.network.utils import robust_send, prepare_message
    run_inner = True
    for obj in mpi.pending_systems_commands:
        cmd, connection = obj
        # Handle the message in a big if-statement. When / if the number
        # of commands escalades, we should consider moving them away.
        if cmd == constants.CMD_ABORT:
            sys.exit(1)

        elif cmd == constants.CMD_PING:
            # We need to access the rank like this. Calling rank() on the
            # communicator will active this function again. Should be
            # apply some locking?
            msg = prepare_message("PONG", mpi.MPI_COMM_WORLD.comm_group.rank())
            robust_send(connection, msg)

        elif cmd == constants.CMD_MIGRATE_PACK:
            # This is a very complex operation, so we simply pass the
            # mpi instance, connection and other usefull information
            # to a class and let it handle everything.
            from mpi.migrate import MigratePack
            migration = MigratePack(mpi, connection, bypassed)

            run_inner = run_inner and migration.mpi_continue()

    mpi.pending_systems_commands = []
    return run_inner

