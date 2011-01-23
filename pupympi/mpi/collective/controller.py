from mpi.collective.cache import Cache
from mpi.logger import Logger
from mpi import constants

from mpi.collective.request.bcast import FlatTreeBCast

class Controller(object):
    def __init__(self, communicator):
        # Setup a global cache. The get / set methods for the cache will be
        # curryed when added to each request. This means that each request will
        # access the global cache, but with a preset prefix.
        self.cache = Cache()

        # Extract some basic elements from the communicator.
        self.size = communicator.comm_group.size()
        self.rank = communicator.comm_group.rank()

        # Set other elements.
        self.communicator = communicator
        self.mpi = communicator.mpi

        # Setup the tag <-> request type mapping. For each tag, a list of
        # possible request classes are defined. When starting a new request,
        # the first class accepting the data is created and executed.
        self.cls_mapping = {
            constants.TAG_BCAST : [FlatTreeBCast],
            constants.TAG_BARRIER : [],
            constants.TAG_ALLREDUCE : [],
            constants.TAG_REDUCE : [],
            constants.TAG_ALLTOALL : [],
            constants.TAG_SCATTER : [],
            constants.TAG_ALLGATHER : [],
            constants.TAG_GATHER : [],
            constants.TAG_SCAN : [],
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
            obj = req_class.accept(self.communicator, *args, **kwargs)
            if obj:
                # Set the tag on the object.
                obj.tag = tag

                # Add the object to the MPI environment and send the start signal.
                with self.mpi.unstarted_collective_requests_lock:
                    self.mpi.unstarted_collective_requests.append(obj)

                    # Signal
                    self.mpi.unstarted_collective_requests_has_work.set()
                    self.mpi.has_work_event.set()

                return obj

        # Note: If we define a safety net we could select the first / last class
        # and initialize that.
        Logger().warning("Unable to initialize the collective request for tag %s. I suspect failure from this point" % tag)

