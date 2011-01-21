from mpi.collective.cache import Cache
from mpi import constants

class Controller(object):
    def __init__(self, communicator):
        # Setup a global cache. The get / set methods for the cache will be
        # curryed when added to each request. This means that each request will
        # access the global cache, but with a preset prefix.
        self.cache = Cache()

        # Extract some basic elements from the communicator, so we do not need
        # to access the communicator object later.
        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        # Setup the tag <-> request type mapping. For each tag, a list of
        # possible request classes are defined. When starting a new request,
        # the first class accepting the data is created and executed.
        self.cls_mapping = {
            constants.TAG_BCAST : [],
            constants.BARRIER : [],
            constants.ALLREDUCE : [],
            constants.REDUCE : [],
            constants.ALLTOALL : [],
            constants.SCATTER : [],
            constants.ALLGATHER : [],
            constants.GATHER : [],
            constants.SCAN : [],
        }

    def get_request(self, tag, *args, **kwargs):
        # Find the first suitable request for the given tag. There is no safety
        # net so if requests are non-exhaustive in their combined accept
        # pattern those not cathed parameters will not return a Request.

        try:
            req_class_list = self.cls_mapping[tag]
        except:
            Logger().warning("Unable to find collective list in the cls_mapping for tag %s" % tag)

        for req_class in req_class_list:
            obj = req_class.accept(self.size, self.rank, *args, **kwargs)
            if obj:
                return obj

        # Note: If we define a safety net we could select the first / last class
        # and initialize that.
        Logger.warning("Unable to initialize the collective request for tag %s. I suspect failure from this point" % tag)


