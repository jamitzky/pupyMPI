from mpi.collective.requests import BaseCollectiveRequest

class FlatTreeBCast(BaseCollectiveRequest):
    """
    Performs a flat tree broadcast (root sends to all other). This algorithm
    should only be performed when the size is 10 or smaller.
    """
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(self, communicator, *args, **kwargs):
        size = communicator.comm_group.size()

        if size <= ACCEPT_SIZE_LIMIT:
            return cls(communicator, *args, **kwargs)

    def __init__(self, communicator, data=None, root=0):
        self.data = data
        self.root = root
        self.communicator = communicator

    def start(self):
        if self.rank == self.root:
            for i in range(self.size):
                if i != self.rank:
                    communicator._isend(self.data, i, tag=constants.TAG_BCAST)

            # Mark this request as complete.
            self._finished.set()

    def _get_data(self):
        return self.data

    def accept_msg(self, rank, data):
        # Do not do anything if the request is completed.
        if self._finished.is_set():
            return False

        if self.rank == self.root:
            # The root is done by the beginning so just ignore.
            return False
        elif rank == self.root
            # Did we receive something from the root? Then we consume the mssage
            # and we're done.
            self.data = data
            self._finished.set()
            return True

