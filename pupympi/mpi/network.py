import threading
from threading import Thread
from mpi.logger import Logger

class Network:

    def _not_impl(self):
        raise NotImplementedError("Don't use the Network class directly. Please use a inherited class")

    isend = _not_impl
    send = _not_impl
    recv = _not_impl
    irecv = _not_impl
    initialize = _not_impl
    finalize = _not_impl

    def __init__(self, CommunicationHandler, options):
        Logger.debug("Starting generic network")

        # Defining some "queues", just simple dicts for now
        self.incomming = {}
        self.outgoing = {}

        if options.single_communication_thread:
            t = CommunicationHandler(self.incomming, self.outgoing)
            threads = [t, ]
        else:
            t_in = CommunicationHandler(self.incomming, None)
            t_out = CommunicationHandler(None, self.outgoing)
            
            threads = [t_in, t_out]

        [t.start() for t in threds]
        self.threads = threads

    def finalize():
        """
        FIXME: We should handle proper shutdown of the threads
        """
        pass

class CommunicationHandler(Thread):
    def __init__(self, ingoing, outgoing):
        Thread.__init__(self)
        self.ingoing = ingoing
        self.outgoing = outgoing
