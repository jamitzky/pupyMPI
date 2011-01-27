from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger

class NaiveScatter(BaseCollectiveRequest):
    def __init__(self, communicator, data=None, root=0):
        super(NaiveScatter, self).__init__()

        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        if root == self.rank:
            chunk_size = len(data) / self.size
            self.data = [ data[r*chunk_size:(r+1)*chunk_size] for r in range(self.size) ]
        else:
            self.data = None

    def start(self):
        if self.root == self.rank:
            children = range(self.size)

            for i in children:
                item = self.data[i]
                if i == self.rank:
                    self.accept_msg(i, item)
                else:
                    self.communicator._isend(item, i, tag=constants.TAG_SCATTER)

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if rank != self.root:
            return False

        self.data = data
        self._finished.set()
        return True

    def _get_data(self):
        return self.data

    ACCEPT_SIZE_LIMIT = 10
    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()
        if size <= cls.ACCEPT_SIZE_LIMIT:
            return cls(communicator, *args, **kwargs)

