from datetime import datetime

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

        # This dict will be sent to the admin caller, who will
        # serialize it (probably with data from other ranks).
        rank = mpi.MPI_COMM_WORLD.comm_group.rank()
        self.data = {
            'rank' : rank,
            'meta' : {
                'pack_start' : datetime.now(),
                },
        }

        # Serialize other data

        # Close down what is needed to close down.

        # Dump the session into a file.

        # Send the data+file on the connection.
        from mpi.network.utils import robust_send, prepare_message
        robust_send(self.socket_connection, prepare_message(self.data, rank))

    def mpi_continue(self):
        """
        Indicating if the MPI environment should try to continue
        after a migration attempt. If the migration is sucessful,
        this will never be called as this class will have called
        sys.exit()
        """
        return not self.success

