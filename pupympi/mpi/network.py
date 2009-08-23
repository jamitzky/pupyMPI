import threading
from threading import Thread
from mpi.logger import Logger

class Network(object):

    def _not_impl(self):
        raise NotImplementedError("Don't use the Network class directly. Please use a inherited class")

    isend = _not_impl
    send = _not_impl
    recv = _not_impl
    irecv = _not_impl
    initialize = _not_impl
    finalize = _not_impl
    start_job = _not_impl

    def __init__(self, CommunicationHandler, options):
        Logger().debug("Starting generic network")

        # Defining some "queues", just simple lists for now
        self.incomming = []
        self.outgoing = []
        self.options = options

        if options.single_communication_thread:
            self.t_in = CommunicationHandler(self.incomming, self.outgoing)
            self.t_out = self.t_in
        else:
            self.t_in = CommunicationHandler(self.incomming, None)
            self.t_out = CommunicationHandler(None, self.outgoing)
            self.t_out.start()

        self.t_in.start()

    def finalize(self):
        """
        FIXME: We should handle proper shutdown of the threads
        """
        pass

class CommunicationHandler(Thread):
    def __init__(self, incomming, outgoing):
        Thread.__init__(self)
        self.incomming = incomming 
        self.outgoing = outgoing

    def add_in_job(self, job):
        self.incomming.append(job)

    def add_out_job(self, job):
        self.outgoing.append(job)
