#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
#
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
from mpi.exceptions import MPIException
from mpi.logger import Logger
from mpi import constants
import mpi.network.utils as utils

import threading

class BaseRequest(object):
    def __init__(self):
        self.status = "new"
        # Start a lock for this request object. The lock should be taken
        # whenever we change the content. It should be legal to read
        # information without locking (like test()). We implement the release() and
        # acquire function on this class directly so the variable stays private
        self._lock = threading.Lock()
        """
        NOTE: This lock is never used. We should consider possible race conditions
        arising from concurrent status updates on a request object. If none are
        plausible we should remove this lock and with it the release and acquire functions
        below.
        """

        # Flag to keep track if the data is pickled. Some methods
        # will pickle directly.
        self.is_pickled = False
        # Flag to signal that header has been appended (and data serialized)
        self.is_prepared = False

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

    def __init__(self, request_type, communicator, participant, tag, acknowledge=False, header=None, data=None, cmd=constants.CMD_USER, multi=False, payload_size=0):
        super(Request, self).__init__()
        if request_type not in ('bcast_send', 'send','recv'):
            raise MPIException("Invalid request_type in request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator
        self.participant = participant # The other process' rank
        self.tag = tag
        self.acknowledge = acknowledge # Boolean indicating that the message requires recieve acknowledgement (for ssend)
        self.data = data # payload
        self.header = header # serialized header for the payload
        self.multi = multi # flag that the request has a list of payloads
        self.payload_size = payload_size # combined bytesize of payloads if single payload this is 0 for now

        self.cmd = cmd
        
        self.global_rank = None # Global rank of recipient process is None for ingoing requests and None for out requests until the request is prepared

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 'new' ->       The object is newly created. If this is send the lower layer can start to
        #                do stuff with the data
        # 'unacked'   -> An ssend that has not been acknowledged yet.
        # 'ready'     -> Means we have the data (in receive) or pickled the data (send) and can
        #                safely return from a test or wait call. For an ssend this means that the
        #                reciever has acknowledged receiving.
        # 'cancelled' -> The user cancelled the request. A some later point this will be removed

        #Logger().debug("Request object created for communicator:%s, tag:%s, data:%s, ack:%s, request_type:%s and participant:%s" % (self.communicator.name, self.tag, self.data, self.acknowledge, self.request_type, self.participant))

    @classmethod
    def from_state(cls, state, mpi):
        communicator = mpi.communicators[state['comm_id']]
        return cls(state['type'], communicator, state['participant'], state['tag'], state['acknowledge'], state['data'], state['cmd'])

    def get_state(self):
        return {
            'type' : self.request_type,
            'cmd' : self.cmd,
            'acknowledge' : self.acknowledge,
            'data' : self.data,
            'participant' : self.participant,
            'tag' : self.tag,
            'comm_id' : self.communicator.id,
        }

    def __repr__(self):
        orig_repr = super(Request, self).__repr__()
        return orig_repr[0:-1] + " type(%s), participant(%d), tag(%d), ack(%s), status(%s), data(%s) >" % (self.request_type, self.participant, self.tag, self.acknowledge, self.status, self.data )

    def prepare_send(self):
        """
        Ready the payload of the request for sending
        
        TODO: Either this function is always called before sending, and so could be folded into Request initialization
              OR it is only called sometimes and so the rationale for calling should be commented here
        """
        # Set global rank to allow the outbound thread to do its socket/rank lookup
        self.global_rank = self.communicator.group().members[self.participant]['global_rank']

        if self.multi:
            self.header = utils.prepare_multiheader(self.communicator.rank(), cmd=self.cmd,
                                           tag=self.tag, ack=self.acknowledge, comm_id=self.communicator.id, payload_length=self.payload_size)
        else:
            if not self.is_prepared:
                # Create the proper data structure and pickle the data
                header,payload = utils.prepare_message(self.data, self.communicator.rank(), cmd=self.cmd,
                                               tag=self.tag, ack=self.acknowledge, comm_id=self.communicator.id, is_serialized=self.is_pickled)
                self.data = payload
                self.header = header
            #DEBUG
            else:
                Logger().debug("Reusing already prepared message")

    def update(self, status, data=None):
        #Logger().debug("- changing status from %s to %s, for data: %s, tag:%s" %(self.status, status, data,self.tag))
        if self.status not in ("finished", "cancelled"): # No updating on dead requests
            self.status = status
        else:
            raise Exception("Updating a request from %s to %s" % self.status, status)

        # We only update if there is data (ie. a recv operation)
        if data is not None:
            self.data = data

        # Enable the wait operation to complete if the status is ready or cancelled
        if status in ("ready", "cancelled"):
            self._waitevent.set()

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        """
        # TODO: The cancel test is simplistic and we should ensure that we can actually cancel in proper MPI fashion
        
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
        """
        #Logger().info("Starting a %s wait, tag: %s" % (self.request_type,self.tag) )

        if self.status == "cancelled":
            #Logger().debug("WAIT on cancel illegality")
            raise MPIException("Illegal to wait on a cancelled request object")

        self._waitevent.wait()
        #Logger().info("Waiting done for request %s wait, tag: %s" % (self.request_type,self.tag) )

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
