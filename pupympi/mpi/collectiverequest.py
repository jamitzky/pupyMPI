import threading, time

from mpi import constants
from mpi.request import BaseRequest, Request
from mpi.exceptions import MPIException
from mpi.logger import Logger

class CollectiveRequest(BaseRequest):

    def __init__(self, request_type, communicator, data=None):
        super(CollectiveRequest, self).__init__()
        if request_type not in ('bcast', 'comm_create','comm_free'): # TODO more needed here
            raise MPIException("Invalid type in collective request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 
        # 'new' ->         The object is newly created. If this is send the lower layer can start to 
        #                  do stuff with the data
        #                  'cancel' is not valid for collective ops: all are blocking.(NBC in mpi2 also cannot be cancelled)
        # 'inprogress' ->  Collective request is in progress but nothing new on the wire
        # 'ready'     ->   Means we have the data (in receive) or pickled the data (send) and can
        #                  safely return from a test or wait call.
        self._m = {'status' : 'new' }

        Logger().debug("CollectiveRequest object created for communicator %s and type %s" % (self.communicator.name, self.request_type))

        if self.request_type == "bcast":
            self.start_bcast(data)

    def start_bcast(self, data):
        """
        From the Communicator.bcast we are only invoking this call if we're
        the root of the bcast. So we find all the receipients and send the
        data to them
        """
        request_objects = []
        for participant in self.communicator.group().members.keys():
            r = Request("bcast_send", self.communicator, participant, constants.TAG_BCAST, data) 
            request_objects.append(r)
            self.communicator.request_add(r)

        [r.wait() for r in request_objects]

    def network_callback(self, lock=True, *args, **kwargs):
        Logger().debug("Network callback in request called")

        if lock:
            self.acquire()

        # FIXME: Handle stuff in here.. DO IT
            
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
        

    # FIXME Deleted test and wait until we know if they'll be needed (copy from Request then)

    def get_status(self):
        return self._m['status']
