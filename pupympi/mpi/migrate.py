from datetime import datetime
import sys, socket
from mpi import dill, MPI, constants
from mpi.communicator import Communicator

class MigratePack(object):
    def __init__(self, mpi, script_hostinfo):
        self.mpi = mpi

        # The bypassed function is the one decorated with
        # handle_system_commands. When the environment is
        # unpacked again this needs to be executed. The format
        # of the variable is a tuple with 3 elements:
        # (function, args, kwargs)
        self.script_hostinfo = script_hostinfo

        self.network = self.mpi.network
        self.t_in = self.network.t_in
        self.t_out = self.network.t_out
        self.pool = self.network.socket_pool

        # Start migration.
        self.pack()

    def pack(self):
        # Find the network threads, as we need direct access to them
        # for extracting state and pause commands.
        if self.t_in.type == "combo":
            self.network_type = "combo"
        else:
            self.network_type = "normal"

        self.rank = self.mpi.MPI_COMM_WORLD.comm_group.rank()

        # This dict will be sent to the admin caller, who will
        # serialize it (probably with data from other ranks).
        self.data = {
            'rank' : self.rank,
            'meta' : {
                'pack_start' : datetime.now(),
                },
            'settings' : {
                'network_type' : self.network_type
            },
        }
        
        # TODO: Fix this comment - what pause are you talkin' 'bout?
        # Pause the threads. Note that pause.set() might be called two times on
        # one network thread, if we are using the combo version.
        self.mpi.shutdown_event.set()
        self.mpi.has_work_event.set()

        self.network.finalize()

        # Make the MPI thread run out if its main loop. We keep it around so
        # the network threads and add messages to it (there might be some on
        # the network layer while we are shuttig down)
        self.mpi.shutdown_event.set() # FIXME: why are we calling this again?
        ###self.mpi.queues_flushed.wait()

        # Make the network send CONN_CLOSE on every socket connection. This way
        # we are sure not to miss messages "on the wire".
        self.close_all_connections()

        # Serialize other data
        self.data['mpi'] = self.mpi.get_state()

        # Remove stuff we can't pickle.
        self.clear_unpickable_objects()

        # Dump the session into a file.
        import tempfile
        _, filename = tempfile.mkstemp(prefix="pupy")

        try:
            dill.dump_session(filename=filename)
            # Load the session data into the dict so we can sent it.
            self.data['session'] = dill.load(open(filename))
        except Exception, e:
            print "Cant serialize the current session. Traceback and information follows:"
            print "\t Error:", e
            import __main__
            print "\t Main session:", __main__.__dict__

        # Send the data+file on the connection.
        from mpi.network.utils import robust_send_multi, prepare_message

        connection = socket.create_connection(self.script_hostinfo, 4.0 )

        header,payloads = prepare_message(dill.dumps(self.data), self.rank, is_serialized=True)
        robust_send_multi(connection, [header]+payloads)

        sys.exit(0)

    def close_all_connections(self):
        from mpi.network import utils as mpi_utils
        import select

        rank = self.mpi.MPI_COMM_WORLD.comm_group.rank()

        # Find all connections in the socket pool.
        write_connections = [ s for s in self.pool.sockets ]
        read_connections = [ s for s in write_connections ]

        # Try to find a socket to -1 (the admin). We don't want to close that one
        with self.pool.sockets_lock:
            admin_conn = self.pool._get_socket_for_rank(-1)

        try:
            write_connections.remove(admin_conn)
        except:
            pass

        try:
            read_connections.remove(admin_conn)
        except:
            pass

        # A list to contain the received objects (not CMD_CONN_CLOSE).
        received_messages = []
        errors_left = 5

        while write_connections or read_connections:
            all_connections = write_connections + read_connections
            rlist, wlist, err_list = select.select(read_connections, write_connections, all_connections, 10)

            if err_list:
                Logger().warning("Received an error list with %d elements: %s" % (len(err_list), err_list))

            # Handle the writes.
            for wsocket in wlist:
                header,payloads = mpi_utils.prepare_message("", rank, cmd=constants.CMD_CONN_CLOSE)
                mpi_utils.robust_send_multi(wsocket, [header]+payloads)
                write_connections.remove(wsocket)

            # Handle the reads.
            for rsocket in rlist:
                try:
                    rank, cmd, tag, ack, comm_id, _, data = mpi_utils.get_raw_message(rsocket)

                    if cmd == constants.CMD_CONN_CLOSE:
                        read_connections.remove(rsocket)
                    else:
                        Logger().info("received important information while closing the sockets.")
                        pass # This message is important. We need to add it to the MPI environment.
                except Exception as e:
                    errors_left -= 1

            if errors_left <= 0:
                break

    def clear_unpickable_objects(self):
        # Let the user remove other elements.
        f = self.mpi.migrate_onpack
        if f:
            f()

        del self.mpi
        del self.network
        del self.t_in.socket_pool
        try:
            del self.t_out.socket_pool
        except:
            pass
        del self.t_in
        del self.t_out

        # Look at the main modules scope. We go through everything in there and
        # delete things we know we can not handle.
        # FIXME: Should this be recursive.
        import __main__
        unwanted = [MPI, Communicator, ]
        for field_name in dir(__main__):
            element = getattr(__main__, field_name, None)

            for enemy in unwanted:
                if isinstance(element, enemy) or enemy == element:
                    delattr(__main__, field_name)

from functools import wraps

def checkpoint(f, *args, **kwargs):
    @wraps(f)
    def inner(mpi, *args, **kwargs):
        # Find the rank:

        migrate = False
        migrate_data = None
        all_commands = []

        rank = mpi.MPI_COMM_WORLD.comm_group.rank()

        # Try to find a migrate command.
        with mpi.pending_systems_commands_lock:
            for obj in mpi.pending_systems_commands:
                cmd, connection, user_data = obj
                if cmd == constants.CMD_MIGRATE_PACK:
                    migrate = True
                    migrate_data = user_data
                else:
                    all_commands.append(obj)

            mpi.pending_systems_commands = all_commands

        if migrate:
            from mpi.migrate import MigratePack
            migration = MigratePack(mpi, migrate_data)

        return f(mpi, *args, **kwargs)

    return inner

if __name__ == "__main__":
    # If this script is called directly it means that we are unpacking.
    mpi = MPI()

