import threading
from mpi.logger import Logger

class Network(threading.Thread):

    def _not_impl(self):
        raise NotImplementedError("Don't use the Network class directly. Please use a inherited class")

    isend = _not_impl
    send = _not_impl
    recv = _not_impl
    irecv = _not_impl
    initialize = _not_impl
    finalize = _not_impl

    def run(self):
        self.initialize()
        Logger().debug("Network: Initialized")
