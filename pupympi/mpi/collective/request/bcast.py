from mpi.collective.requests import BaseCollectiveRequest

class FlatTreeBCast(BaseCollectiveRequest):
    """
    Performs a flat tree broadcast (root sends to all other). This algorithm
    should only be performed when the size is 10 or smaller.
    """
    ACCEPT_SIZE_LIMIT = 10

    @classmethod
    def accept(self, size, rank, *args, **kwargs):
        if size <= ACCEPT_SIZE_LIMIT:
            return cls(size, rank, *args, **kwargs)
