from mpi.collective.request import BaseCollectiveRequest
from mpi import constants
from mpi.logger import Logger

class FlatTreeBCast(BaseCollectiveRequest):
    """
    Performs a flat tree broadcast (root sends to all other). This algorithm
    should only be performed when the size is 10 or smaller.
    """
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(cls, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= cls.ACCEPT_SIZE_LIMIT:
            return cls(communicator, *args, **kwargs)

    def __init__(self, communicator, data=None, root=0):
        super(FlatTreeBCast, self).__init__()

        self.data = data
        self.root = root
        self.communicator = communicator

        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

    def start(self):
        if self.rank == self.root:
            for i in range(self.size):
                if i != self.rank:
                    print "Sending from %d ==> %d" % (self.rank, i)
                    self.communicator._isend(self.data, i, tag=constants.TAG_BCAST)

            # Mark this request as complete.
            self._finished.set()

    def _get_data(self):
        return self.data

    def accept_msg(self, rank, data):
        print "%d <== data received from %d" % (self.rank, rank)
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if self.rank == self.root:
            # The root is done by the beginning so just ignore.
            return False
        elif rank == self.root:
            # Did we receive something from the root? Then we consume the mssage
            # and we're done.
            self.data = data
            self._finished.set()
            return True
        else:
            Logger().warning("What to do with data. rank %d, root %d self.rank %d, data %s" % (rank, self.root, self.rank, data))

