from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi import utils
from mpi.logger import Logger

class NaiveAllToAll(BaseCollectiveRequest):
    """
    A naive all-to-all algorithm, that will outperform most other algorithms
    for this use case.

    .. note::
        This class will expect data to be well-sized. This should be handled in
        the user available API call.
        
    ISSUES:
    - It is possible that it would be more efficient to serialize the whole
      dataset once instead of piecemeal and then slice out portions to send to
      each node
    """
    def __init__(self, communicator, data):
        super(NaiveAllToAll, self).__init__(communicator, data)

        self.data = data
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        # Setup the ranks we still need to hear from.
        self.missing_participants = range(self.size)
        self.missing_participants.remove(self.rank)

        # A list with integers. We will replace the contents in the
        # accept_msg function.
        self.received_data = range(self.size)

        self.tag = constants.TAG_ALLTOALL

    @classmethod
    def accept(cls, communicator, settings,  cache, *args, **kwargs):
        # FIXME: Should it be possible to inherit an accept method that will
        # simply accept with the basic parameters?
        return cls(communicator, *args, **kwargs)

    def start(self):
        # Get own data

        # slice the data and send it to each participant.
        chunk_size = len(self.data) / self.size
        for r in range(self.size):
            data = self.data[r*chunk_size:(r+1)*chunk_size]            
            if r == self.rank:
                # msg to self bypasses queues
                self.received_data[self.rank] = data
            else:                
                self.isend(data, r, self.tag)

    def accept_msg(self, rank, raw_data, msg_type):

        # A finished request does not accept messages.
        if self._finished.is_set():            
            return False

        # And we only accept messages from the ones we havn't hear from
        if rank not in self.missing_participants:
            return False
        else:
            self.missing_participants.remove(rank) # we accept (but only once)
            
        # Deserialize data
        data = utils.deserialize_message(raw_data, msg_type)

        # Insert the data at the proper place.
        self.received_data[rank] = data

        # If we dont need to hear from anyone else we mark the request as finished,
        # clean data first.
        if len(self.missing_participants) == 0:
            self.clean_data()
            self.done()

        return True

    def clean_data(self):
        if isinstance(self.data, str):
            self.data = ''.join(self.received_data)

        # Check if tuple (we need to tuplify)
        elif isinstance(self.data,tuple):
            self.data = tuple([ item for sublist in self.received_data for item in sublist ])
        else:
            self.data = [ item for sublist in self.received_data for item in sublist ] # Get results for own rank

    def _get_data(self):
        return self.data

