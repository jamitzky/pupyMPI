from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger

from math import log

class DisseminationAllGather(BaseCollectiveRequest):
    def __init__(self, communicator, data):
        super(DisseminationAllGather, self).__init__()

        self.data = data
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

    def start(self):
        # Do some initial calculation.
        self.data_list = [None] * self.size
        self.data_list[self.rank] = self.data

        self.iterations = int(log(self.size, 2))
        self.gap_size = self.size - 2**self.iterations
        self.i = 0

        self.phase = "normal"

        self.iterate()

    @classmethod
    def accept(cls, *args, **kwargs):
        """
        This implementation is so supreme that we accept problems of any sizes
        and layout. GO TEAM DISSEMINATION.
        """
        return cls(*args, **kwargs)

    def iterate(self):
        send_to = (2**self.i+self.rank) % self.size
        self.recv_from = (self.rank - (2**self.i)) % self.size

        self.communicator._isend(self.data_list, send_to, constants.TAG_ALLGATHER)

    def accept_msg(self, rank, data):
        if self._finished.is_set() or rank != self.recv_from:
            return False

        if self.phase == "normal":
            # process data
            for e in range(self.size):
                if data[e] is not None:
                    self.data_list[e] = data[e]

            # bump iteration
            self.i += 1

            # next iteration
            if self.i < self.iterations:
                self.iterate()
            else:
                self.odd()

            return True
        elif self.phase == "odd":
            my_gap_start = self.rank+1
            j = 0
            for gdx in range(my_gap_start,my_gap_start+self.gap_size):
                idx = gdx % self.size
                gap_item = data[j]
                self.data_list[idx] = gap_item
                j += 1
            self.finish()
            return True
        else:
            Logger().warning("accept_msg in unkown phase: %s" % self.phase)

        return False

    def odd(self):
        if self._finished.is_set():
            return

        # Check if there are odd messages
        if not self.gap_size:
            return self.finish()

        self.phase = "odd"

        send_to = (self.rank + 2**self.i) % self.size
        self.recv_from = (self.rank - 2**self.i) % self.size

        # Get missing gap
        gap_start = send_to+1
        gap = self.data_list[gap_start:gap_start+self.gap_size]
        # Check if the gap wraps around
        gap_wrap = self.gap_size - len(gap)
        if gap_wrap:
            gap = gap+self.data_list[0:gap_wrap]

        s_handle = self.communicator._isend(gap, send_to, constants.TAG_ALLGATHER)

    def finish(self):
        self.data = self.data_list
        self._finished.set()

    def _get_data(self):
        return self.data
