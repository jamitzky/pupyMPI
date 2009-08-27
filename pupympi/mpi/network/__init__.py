import threading
from threading import Thread
from mpi.logger import Logger

class AbstractNetwork(object):

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
        rank = options.rank

        if options.single_communication_thread:
            self.t_in = CommunicationHandler(rank, self.incomming, self.outgoing)
            self.t_out = self.t_in
        else:
            self.t_in = CommunicationHandler(rank, self.incomming, None)
            self.t_out = CommunicationHandler(rank, None, self.outgoing)
            self.t_out.start()

        self.t_in.start()

    def get_received_data(self, participant, tag, communicator):
        return self.t_in.get_received_data(participant, tag, communicator)

    def finalize(self):
        """
        Forwarding the finalize call to the threads. Look at the 
        CommunicationHandler.finalize for a deeper description of
        the shutdown procedure. 
        """
        self.t_in.finalize()
        if not self.options.single_communication_thread:
            self.t_out.finalize()

class AbstractCommunicationHandler(Thread):
    def __init__(self, rank, incomming, outgoing):
        Thread.__init__(self)
        self.incomming = incomming 
        self.outgoing = outgoing
        self.rank = rank

        self.shutdown_lock = threading.Lock()
        self.shutdown_lock.acquire()

    def add_in_job(self, job):
        self.incomming.append(job)

    def add_out_job(self, job):
        self.outgoing.append(job)

    def shutdown_ready(self):
        acquired = self.shutdown_lock.acquire(False)
        if acquired:
            self.shutdown_lock.release()

        Logger().debug("CommunicationHandler asked for shutdown status: %s" % acquired)
        return acquired

    def finalize(self):
        """
        When each thread starts a shutdown lock is acquired. As long as this
        lock is taken the thread can't shut down. So when finalized is called
        we release the lock. 

        This mean that the shutdown_ready() funtion can acquire it. This is used
        in the main run loop and allows the thread to break out of the while True
        loop. 
        """
        self.shutdown_lock.release()
