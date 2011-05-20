import threading, sys

from mpi.topology import tree

class BaseCollectiveRequest(object):
    def __init__(self, *args, **kwargs):
        self.tag = None

        # This object (with the acquire() and release() methods) defiend below
        # opens for the pythoic way to lock an object (with-keyword)
        self._lock = threading.Lock()
        self._finished = threading.Event()

    def acquire(self):
        """
        The central request object. This is an internal locking facility
        for securing atomic access to the object.

        This function acquires the lock.
        """
        self._lock.acquire()

    def release(self):
        """
        This function releases the lock.
        """
        self._lock.release()

    def test(self):
        """
        Test if the collective operation is finished. That is if the :func:`wait`
        function will return right away.
        """
        return self._finished.is_set()

    def wait(self):
        """
        Wait until the collective operation has finihsed and then return the data.
        """
        self._finished.wait()

        # Requests are free to override this method, and implement their own
        # wait(), but it is probably not needed. Look into writing a _get_data
        # method instead.
        f = getattr(self, "_get_data", None)
        if callable(f):
            return f()
        else:
            return getattr(self, "data", None)

    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        raise NotImplementedError("The accept() method was not implemented by the inheriting class.")

    def accept_msg(self, *args, **kwargs):
        raise NotImplementedError("The accept_msg() method was not implemented by the inheriting class.")

    def start(self):
        raise NotImplementedError("The start() method was not implemented by the inheriting class.")

def get_accept_range(cls, settings, prefix="BINOMIAL_TREE"):
    # This method will check if there should exist
    # any settings for this particular algorithm and
    # tree type. If so these are used. If not the generic
    # limits will be inspected 
    accept_min = None
    accept_max = None
    class_prefix = getattr(cls, "SETTINGS_PREFIX", "")
    
    # Sanitise the names a bit. 
    if prefix:
        prefix = prefix.strip("_") + "_"
        
    if class_prefix:
        class_prefix = class_prefix.strip("_") + "_"
    
    accept_min = getattr(settings, class_prefix + prefix + "MIN", None)
    accept_max = getattr(settings, class_prefix + prefix + "MAX", None)

    if accept_min is None:
        accept_min = getattr(settings, prefix + "MIN", 0)
    
    if accept_max is None:
        accept_max = getattr(settings, prefix + "MAX", sys.maxint)

    return accept_min, accept_max

class FlatTreeAccepter(object):
    """
    Inherit from this class for objects that needs to accept a
    static tree. This class produces a simple accept method that
    will look into simple setting objects for accepting.
    """
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="FLAT_TREE")
        
        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_static_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.FlatTree(communicator, root=root)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj
 
class BinomialTreeAccepter(object):
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="BINOMIAL_TREE")

        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_binomial_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.BinomialTree(communicator, root=root)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj

class StaticFanoutTreeAccepter(object):
    # Fetch the fanout parameter from settings as well.
    @classmethod
    def accept(cls, communicator, settings, cache, *args, **kwargs):
        accept_min, accept_max = get_accept_range(cls, settings, prefix="STATIC_FANOUT")

        size = communicator.comm_group.size()
        if size >= accept_min and size <= accept_max:
            obj = cls(communicator, *args, **kwargs)
            
            # Check if the topology is in the cache.
            root = kwargs.get("root", 0) 
            cache_idx = "tree_static_%d" % root
            topology = cache.get(cache_idx, default=None)
            if not topology:
                topology = tree.StaticFanoutTree(communicator, root=root, fanout=communicator.mpi.settings.STATIC_TREE_FANOUT_COUNT)
                cache.set(cache_idx, topology)
    
            obj.topology = topology
            return obj
