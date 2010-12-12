from datetime import datetime
import dill, sys

class MigratePack(object):
    def __init__(self, mpi, socket_connection, bypassed_function):
        self.mpi = mpi
        self.socket_connection = socket_connection
        self.success = False

        # The bypassed function is the one decorated with
        # handle_system_commands. When the environment is
        # unpacked again this needs to be executed. The format
        # of the variable is a tuple with 3 elements:
        # (function, args, kwargs)
        self.bypassed_function = bypassed_function

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

        self.network.finalize(close_sockets=False)

        # Serialize other data
#       self.data['mpi'] = self.mpi.get_state()
#       self.data['t_out'] = self.t_out.get_state()
#       self.data['t_in'] = self.t_in.get_state()
#       self.data['bypassed'] = self.bypassed_function

        # Close down what is needed to close down.
        try:
            del threading # more
        except UnboundLocalError:
            print "Can't unset threading"

        # Dump the session into a file.
        import tempfile
        _, filename = tempfile.mkstemp(prefix="pupy")

        try:
            dill.dump_session(filename=filename)

            # Load the session data into the dict so we can sent it.
            self.data['session'] = dill.load(open(filename))
        except:
            print "Cant pickle the current session into a file"

        # Send the data+file on the connection.
        from mpi.network.utils import robust_send, prepare_message

        if self.rank == 0:
            print "data", self.data
            print "connection", self.socket_connection


        robust_send(self.socket_connection, prepare_message(self.data, self.rank))

        sys.exit(0)

    def mpi_continue(self):
        """
        Indicating if the MPI environment should try to continue
        after a migration attempt. If the migration is sucessful,
        this will never be called as this class will have called
        sys.exit()
        """
        return not self.success

