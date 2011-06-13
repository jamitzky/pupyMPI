from mpi.collective.cache import Cache
from mpi.logger import Logger
from mpi import constants
from mpi.collective.request import bcast, reduce, alltoall, gather, scatter, barrier

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
            # Non-used bcast algorithms: bcast.RingBCast
            constants.TAG_BCAST : [bcast.FlatTreeBCast, bcast.BinomialTreeBCast, bcast.StaticFanoutTreeBCast],

            # Non-used barrier algorithms: barrier.RingBarrier
            #constants.TAG_BARRIER : [barrier.FlatTreeBarrier, barrier.BinomialTreeBarrier, barrier.StaticFanoutTreeBarrier],
            constants.TAG_BARRIER : [barrier.BinomialTreeBarrier, barrier.StaticFanoutTreeBarrier],
            constants.TAG_ALLREDUCE : [reduce.FlatTreeAllReduce, reduce.BinomialTreeAllReduce, reduce.StaticTreeAllReduce],
            constants.TAG_REDUCE : [reduce.FlatTreeReduce, reduce.BinomialTreeReduce, reduce.StaticTreeReduce],
            constants.TAG_ALLTOALL : [alltoall.NaiveAllToAll],
            constants.TAG_SCATTER : [scatter.BinomialTreeScatterPickless, scatter.FlatTreeScatter, scatter.BinomialTreeScatter, scatter.StaticFanoutTreeScatter],
            constants.TAG_ALLGATHER : [gather.DisseminationAllGatherPickless, gather.DisseminationAllGather],
            constants.TAG_GATHER : [gather.BinomialTreeGatherPickless,gather.FlatTreeGather, gather.BinomialTreeGather, gather.StaticFanoutTreeGather],
            constants.TAG_SCAN : [reduce.FlatTreeScan, reduce.BinomialTreeScan, reduce.StaticFanoutTreeScan],
        }
        
        self.generate_class_ids()
        
    def generate_class_ids(self):
        """
        Run though the above list of collective requests and give them a unique ID. This enables 
        us to add this ID in the payload header when sending messages. This in turn enables us to
        alter the primary selected request type based on the id. 
        """
        self.class_ids = {}
        
        id = 0
        for tag in self.cls_mapping:
            for cls in self.cls_mapping[tag]:
                cls.__coll_class_id = id
                self.class_ids[id] = cls
                id += 1

    def get_request(self, tag, *args, **kwargs):
        # Find the first suitable request for the given tag. There is no safety
        # net so if requests are non-exhaustive in their combined accept
        # pattern those not cathed parameters will not return a Request.

        try:
            req_class_list = self.cls_mapping[tag]
        except:
            Logger().warning("Unable to find collective list in the cls_mapping for tag %s" % tag)

        for req_class in req_class_list:
            obj = req_class.accept(self.communicator, self.communicator.mpi.settings, self.cache, *args, **kwargs)
            #Logger().debug("rank:%i has %s for req_class:%s arg:%s" % (self.rank,bool(obj), req_class.__name__, kwargs['data']) )
            if obj:
                # Set the tag on the object.
                obj.tag = tag

                # Add the object to the MPI environment and send the start signal.
                with self.mpi.unstarted_collective_requests_lock:
                    self.mpi.unstarted_collective_requests.append(obj)

                    # Signal
                    self.mpi.unstarted_collective_requests_has_work.set()
                    self.mpi.has_work_event.set()
                    # DEBUG
                    #Logger().debug("adding and signalled allgather req obj")

                return obj

        # Note: If we define a safety net we could select the first / last class
        # and initialize that.
        Logger().warning("Unable to initialize the collective request for tag %s. I suspect failure from this point" % tag)
        
