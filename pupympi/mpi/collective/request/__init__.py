import threading

class BaseCollectiveRequest(object):
    def __init__(self):
        self.tag = None

        # This object (with the acquire() and release() methods) defiend below
        # opens for the pythoic way to lock an object (with-keyword)
        self._lock = threading.Lock()
        self._finished = threading.Event()

    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def test(self):
        """
        Document me.
        """
        return self._finished.is_set()

    def wait(self):
        """
        Document me
        """
        self._finished.wait()

        # Requests are free to override this method, and implement their own
        # wait(), but it is probably not needed. Look into writing a _get_data
        # method instead.
        f = getattr(self, "_get_data", None)
        if callable(f):
            return f()

    @classmethod
    def accept(self, size, rank, *args, **kwargs):
        raise NotImplementedError("The accept() method was not implemented by the inheriting class.")

    def accept_msg(self, *args, **kwargs):
        raise NotImplementedError("The accept_msg() method was not implemented by the inheriting class.")

    def start(self):
        raise NotImplementedError("The start() method was not implemented by the inheriting class.")
