from mpi.exceptions import MPIException
from mpi.logger import Logger
import threading, time

class CollectiveRequest:

    def __init__(self, type, communicator, participants, tag, data=None):
        if type not in ('comm_create','comm_free'): # TODO more needed here
            raise MPIException("Invalid type in collective request creation. This should never happen. ")

        self.type = type
        self.communicator = communicator
        self.participants = participants
        self.tag = tag # TODO determine if this is needed for collective ops
        self.data = data

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 'new' ->       The object is newly created. If this is send the lower layer can start to 
        #                do stuff with the data
        # 'inprogress' -> collective request is in progress but nothing new on the wire
        # 'partialready' -> a partial part of the collective request is completed and the partial set of data can be picked up
        # 'cancelled' -> The request was cancelled. Maybe this is not needed for collective ops
        # 'ready'     -> Means we have the data (in receive) or pickled the data (send) and can
        #                safely return from a test or wait call.
        self._m = {'status' : 'new' }

        # Start a lock for this request object. The lock should be taken
        # whenever we change the content. It should be legal to read 
        # information without locking (like test()). We implement the release() and
        # acquire function on this class directly so the variable stays private
        self._m['lock'] = threading.Lock()

        Logger().debug("Request object created for communicator %s, tag %s and type %s and participants %s" % (self.communicator.name, self.tag, self.type, self.participants))

        callbacks = [ self.network_callback, ]

        # Start the network layer on a job as well
        self.communicator.network.start_job(self, self.communicator, type, self.participant, tag, data, callbacks=callbacks)

    def network_callback(self, lock=True, *args, **kwargs):
        Logger().debug("Network callback in request called")

        if lock:
            self.acquire()

        if "status" in kwargs:
            Logger().info("Updating status in request from %s to %s" % (self._m["status"], kwargs["status"]))
            self._m["status"] = kwargs["status"]
            
        if "data" in kwargs:
            Logger().info("Adding data to request object")
            self.data = kwargs["data"]
            
        if lock:
            self.release()

    def release(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._m['lock'].release(*args, **kwargs)

    def acquire(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._m['lock'].acquire(*args, **kwargs)

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self._m['status'] = 'cancelled'
        Logger().debug("Cancelling a %s request" % self.type)
        

    def wait(self):
        """
        Blocks until the request data can be garbage collected. This method can be used
        to create stable methods limiting the memory usage by not creating new send
        requests before the ressources for the current one has been removed.

        When waiting for a receive, the data will be returned to the calling function.

        On successfull completion the ressources occupied by this request object will
        be garbage collected.

        FIXME: This should probably be a bit more thread safe. Should we add a lock to 
               each request object and lock it when we look at it?
        """
        Logger().info("Starting a %s wait" % self.type)
        while not self.test():
            time.sleep(1)

        # We're done at this point. Set the request to be completed so it can be removed
        # later.
        self._m['status'] = 'finished'

        # Return none or the data
        if self.type == 'recv':
            return self.data

        Logger().info("Ending a %s wait" % self.type)

    def test(self):
        """
        A non-blocking check to see if the request is ready to complete. If true a 
        following wait() should return very fast.
        """
        Logger().debug("Testing a %s request" % self.type)
        return self._m['status'] == 'ready'

    def get_status(self):
        return self._m['status']
