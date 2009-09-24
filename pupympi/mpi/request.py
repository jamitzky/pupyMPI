from mpi.exceptions import MPIException
from mpi.logger import Logger
import threading, time

class BaseRequest(object):
    def __init__(self):
        self._m = {'status' : 'new' }
        # Start a lock for this request object. The lock should be taken
        # whenever we change the content. It should be legal to read 
        # information without locking (like test()). We implement the release() and
        # acquire function on this class directly so the variable stays private
        self._m['lock'] = threading.Lock()

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

class Request(BaseRequest):

    def __init__(self, request_type, communicator, participant, tag, data=None):
        super(Request, self).__init__()
        if request_type not in ('bcast_send', 'send','recv'):
            raise MPIException("Invalid request_type in request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator
        self.participant = participant
        self.tag = tag
        self.data = data

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 'new' ->       The object is newly created. If this is send the lower layer can start to 
        #                do stuff with the data
        # 'cancelled' -> The user cancelled the request. A some later point this will be removed
        # 'ready'     -> Means we have the data (in receive) or pickled the data (send) and can
        #                safely return from a test or wait call.

        Logger().debug("Request object created for communicator %s, tag %s and request_type %s and participant %s" % (self.communicator.name, self.tag, self.request_type, self.participant))

        callbacks = [ self.network_callback, ]

        # Start the network layer on a job as well
        self.communicator.network.start_job(self, self.communicator, request_type, self.participant, tag, data, callbacks=callbacks)

        # If we have a request object we might already have received the
        # result. So we look into the internal queue to see. If so, we use the
        # network_callback method to update all the internal structure.
        if request_type == 'recv':
            data = communicator.pop_unhandled_message(participant, tag)
            if data:
                self.network_callback(lock=False, status="ready", data=data['data'])
                return
            
        # Start a waiting lock. We use this as an alternative way to test if the
        # request is ready in the user level code. We acquire the lock when we
        # create the object. A wait() will make a blocking accuire on that lock
        # and only get it when the lock is released. 
        self._m['waitlock'] = threading.Lock()
        self._m['waitlock'].acquire()

    def network_callback(self, lock=True, *args, **kwargs):
        Logger().debug("Network callback in request called")

        if lock:
            self.acquire()

        if "status" in kwargs:
            Logger().info("Updating status in request from %s to %s" % (self._m["status"], kwargs["status"]))
            self._m["status"] = kwargs["status"]

            if kwargs["status"] == "ready" and "waitlock" in self._m:
                self._m['waitlock'].release()
            
        if "data" in kwargs:
            Logger().info("Adding data to request object")
            self.data = kwargs["data"]
            
        if lock:
            self.release()

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self._m['status'] = 'cancelled'
        Logger().debug("Cancelling a %s request" % self.request_type)

        # We release the wait lock. FIXME: Is this right? 
        self._m['waitlock'].release()
        

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
        Logger().info("Starting a %s wait" % self.request_type)
        
        if "waitlock" in self._m:
            self._m['waitlock'].acquire()
            self._m['waitlock'].release()

        # We're done at this point. Set the request to be completed so it can be removed
        # later.
        self._m['status'] = 'finished'

        # Return none or the data
        if self.request_type == 'recv':
            return self.data

        Logger().info("Ending a %s wait" % self.request_type)

    def test(self):
        """
        A non-blocking check to see if the request is ready to complete. If true a 
        following wait() should return very fast.
        """
        Logger().debug("Testing a %s request" % self.request_type)
        return self._m['status'] == 'ready'

    def get_status(self):
        return self._m['status']
