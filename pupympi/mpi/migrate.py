from datetime import datetime
import sys, socket
from mpi import dill

class Migrate(object):
    def __init__(self, mpi, bypassed_function, script_hostinfo):
        self.mpi = mpi
        self.success = False

        # The bypassed function is the one decorated with
        # handle_system_commands. When the environment is
        # unpacked again this needs to be executed. The format
        # of the variable is a tuple with 3 elements:
        # (function, args, kwargs)
        self.bypassed_function = bypassed_function
        self.script_hostinfo = script_hostinfo

        # Start migration.
        self.pack()

    def pack(self):
        # Find the network threads, as we need direct access to them
        # for extracting state and pause commands.
        self.network = self.mpi.network
        self.t_in = self.network.t_in
        self.t_out = self.network.t_out
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

        # Pause the threads. Note that pause.set() might be called two times on
        # one network thread, if we are using the combo version.
        self.mpi.shutdown_event.set()
        self.mpi.has_work_event.set()

        self.network.finalize()

        # Make the MPI thread run out if its main loop. We keep it around so
        # the network threads and add messages to it (there might be some on
        # the network layer while we are shuttig down)
        mpi.shutdown_event.set()
        mpi.queues_flushed.wait()

        # Make the network send CONN_CLOSE on every socket connection. This way
        # we are sure not to miss messages "on the wire".
        self.close_all_connections()

        self.clear_unpickable_objects()

        # Serialize other data
        self.data['mpi'] = self.mpi.get_state()
        self.data['t_out'] = self.t_out.get_state()
        self.data['t_in'] = self.t_in.get_state()
        self.data['bypassed'] = self.bypassed_function

        # Dump the session into a file.
        import tempfile
        _, filename = tempfile.mkstemp(prefix="pupy")

        try:
            dill.dump_session(filename=filename)

            # Load the session data into the dict so we can sent it.
            self.data['session'] = dill.load(open(filename))
        except Exception as e:
            print "Cant pickle the current session into a file", e

        # Send the data+file on the connection.
        from mpi.network.utils import robust_send, prepare_message

        connection = socket.create_connection(self.script_hostinfo, 4.0 )

        msg = prepare_message(dill.dumps(self.data), self.rank, is_pickled=True)
        robust_send(connection, msg)

        sys.exit(0)

    def close_all_connections(self):
        pass

    def mpi_continue(self):
        """
        Indicating if the MPI environment should try to continue
        after a migration attempt. If the migration is sucessful,
        this will never be called as this class will have called
        sys.exit()
        """
        return not self.success

    def clear_unpickable_objects(self):
        del self.mpi
        del self.network
        del self.t_in.socket_pool
        try:
            del self.t_out.socket_pool
        except:
            pass
        del self.t_in
        del self.t_out

        # This might be freaky stuff..
        import __main__
        del __main__.MPI
        del __main__.mpi
        del __main__.world

