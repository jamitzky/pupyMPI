from mpi.exceptions import MPIException
from mpi.logger import Logger
from mpi.network.utils import _nice_data # FIXME: up import level to make explicit

import threading, time

class BaseRequest(object):
    def __init__(self):
        self.status = "new"
        # Start a lock for this request object. The lock should be taken
        # whenever we change the content. It should be legal to read 
        # information without locking (like test()). We implement the release() and
        # acquire function on this class directly so the variable stays private
        self._lock = threading.Lock()
        
        # Start an event for waiting on the request
        self._waitevent = threading.Event()
        
    def release(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._lock.release(*args, **kwargs)

    def acquire(self, *args, **kwargs):
        """
        Just forwarding method call to the internal lock
        """
        return self._lock.acquire(*args, **kwargs)

class Request(BaseRequest):

    def __init__(self, request_type, communicator, participant, tag, acknowledge=False, data=None):
        super(Request, self).__init__()
        if request_type not in ('bcast_send', 'send','recv'):
            raise MPIException("Invalid request_type in request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator
        self.participant = participant # The other process' rank
        self.tag = tag
        self.acknowledge = acknowledge # Boolean indicating that the message requires recieve acknowledgement (for ssend)
        self.data = data

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 'new' ->       The object is newly created. If this is send the lower layer can start to 
        #                do stuff with the data
        # 'unacked'   -> An ssend that has not been acknowledged yet.
        # 'ready'     -> Means we have the data (in receive) or pickled the data (send) and can
        #                safely return from a test or wait call. For an ssend this means that the
        #                reciever has acknowledged receiving.
        # 'cancelled' -> The user cancelled the request. A some later point this will be removed

        Logger().debug("Request object created for communicator %s, tag %s, data %s, ack %s and request_type %s and participant %s" % (self.communicator.name, self.tag, self.data, self.acknowledge, self.request_type, self.participant))
    
    def __repr__(self):        
        
        orig_repr = super(Request, self).__repr__()
        return orig_repr[0:-1] + " type(%s), participant(%d), tag(%d), ack(%s), status(%s), data(%s) >" % (self.request_type, self.participant, self.tag, self.acknowledge, self.status, _nice_data(self.data) )
    
    def update(self, status, data=None):
        Logger().debug("changing status from %s to %s, for data: %s" %(self.status, status, data))
        if self.status not in ("finished", "cancelled"): # No updating on dead requests
            self.status = status
        else:
            raise Exception("Updating a request from %s to %s" % self.status, status)
        
        # We only update if there is data (ie. a recv operation)
        #NOTE: Even if a send includes the data parameter it is only a superflous overwrite
        if data:
            self.data = data
            
        # If the status is ready we're enabling the wait operation
        # to complete
        if status in ("ready", "cancelled"):
            self._waitevent.set()

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self.update("cancelled")
        
    def test_cancelled(self):
        """
        Returns True if this request was cancelled. 
        """
        return self.status == "cancelled"
    
    def wait(self):
        """
        Blocks until the request data can be garbage collected. This method can be used
        to create stable methods limiting the memory usage by not creating new send
        requests before the ressources for the current one has been removed.

        When waiting for a receive, the data will be returned to the calling function.

        On successfull completion the ressources occupied by this request object will
        be garbage collected.
               
        FIXME: The C version of wait() returns always a status, but we're returning data
               as it's the best thing in python. Maybe it would make sense to return a
               tuple containing something like (status, data). 
        """
        #Logger().info("Starting a %s wait" % self.request_type)
        
        if self.status == "cancelled":
            Logger().debug("WAIT on cancel illegality")
            raise MPIException("Illegal to wait on a cancelled request object")
        
        self._waitevent.wait()
        Logger().debug("Waiting done for request with data:%s" % _nice_data(self.data) )
        
        # We're done at this point. Set the request to be completed so it can be removed
        # later.
        self.status = 'finished'

        # Return none or the data
        if self.request_type == 'recv':
            return self.data

    def test(self):
        """
        A non-blocking check to see if the request is ready to complete. If true a 
        following wait() should return very fast.
        """
        return self._waitevent.is_set()