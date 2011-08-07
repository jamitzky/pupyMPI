from mpi.collective.request import BaseCollectiveRequest
from mpi.commons import numpy
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

class NaiveAllToAllPickless(BaseCollectiveRequest):
    """
    An naive all-to-all algorithm, for pickless types

    .. note::
        This class will expect data to be well-sized. This should be handled in
        the user available API call.
        
    ISSUES:
    - It is possible that it would be more efficient to serialize the whole
      dataset once instead of piecemeal and then slice out portions to send to
      each node
    """
    def __init__(self, communicator, data):
        super(NaiveAllToAllPickless, self).__init__(communicator, data)
        
        # DEBUG
        import copy        
        #self.data, self.msg_type,_ = utils.serialize_message(copy.deepcopy(data))
        self.data, self.msg_type,_ = utils.serialize_message(data)
        self.chunksize = len(self.data[-1]) # we don't send shapebytes and so, don't count them if they are there
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
        #Logger().warning("PICKLESS! now also for all2all! chunksize:%s len:%s" % (self.chunksize, len(self.data[-1])) )

    @classmethod
    def accept(cls, communicator, settings,  cache, *args, **kwargs):
        """
        Accept as long as it is numpy array or bytearray
        """
        if isinstance(kwargs['data'], numpy.ndarray) or isinstance(kwargs['data'],bytearray):
            return cls(communicator, *args, **kwargs)

    def start(self):
        # Get own data
        #Logger().debug("self.data:%s vs self.received_data:%s" % (self.data,self.received_data) )
        # slice the data and send it to each participant.
        chunk_size = self.chunksize / self.size
        for r in range(self.size):
            data = self.data[-1][r*chunk_size:(r+1)*chunk_size]            
            if r == self.rank:
                # msg to self bypasses queues
                self.received_data[self.rank] = data
            else:
                #Logger().debug("start sending data-len:%s  chunk_size:%s self.data:%s data:%s" % (len(data), chunk_size, self.data, data) )
                self.multisend([data], r, tag=constants.TAG_ALLTOALL, cmd=self.msg_type, payload_length=chunk_size)
                #self.isend(data, r, self.tag)

    def accept_msg(self, rank, raw_data, msg_type):

        # A finished request does not accept messages.
        if self._finished.is_set():            
            return False

        # And we only accept messages from the ones we havn't hear from
        if rank not in self.missing_participants:
            return False
        else:
            self.missing_participants.remove(rank) # we accept (but only once)
            
        # Insert the data at the proper place
        self.received_data[rank] = raw_data

        # If we dont need to hear from anyone else we mark the request as finished,
        # clean data first.
        if len(self.missing_participants) == 0:
            #self.clean_data() # Doing it in _getdata instead
            self.done()

        return True

    def clean_data(self):
        """
        insert the received data into the original array
        """
        chunk_size = self.chunksize / self.size
        for i,data in enumerate(self.received_data):
            if i == self.rank:
                self.data[-1][i*chunk_size:(i+1)*chunk_size] = data
            else:
                self.data[-1][i*chunk_size:(i+1)*chunk_size] = numpy.fromstring(data,numpy.uint8)
                

    def _get_data(self):
        import copy
        tempdata = copy.deepcopy(self.data)
        chunk_size = self.chunksize / self.size
        #Logger().debug("BEFORE tempdata:%s self.received:%s" % (tempdata, self.received_data) )
        #Logger().debug("cleaning BEFORE self.data:%s self.received:%s" % (self.data, self.received_data) )
        for i,data in enumerate(self.received_data):
            if i == self.rank:
                tempdata[-1][i*chunk_size:(i+1)*chunk_size] = data
            else:
                tempdata[-1][i*chunk_size:(i+1)*chunk_size] = numpy.fromstring(data,numpy.uint8)

        #Logger().debug("AFTER tempdata:%s self.received:%s" % (tempdata, self.received_data) )
        data = utils.deserialize_message(tempdata, self.msg_type)
        return data