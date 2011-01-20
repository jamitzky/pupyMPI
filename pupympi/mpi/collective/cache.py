class CacheIndexException(Exception):
    pass

class Cache(object):
    def __init__(self):
        self.content = {}

    def set(self, key, content, prefix=""):
        key = prefix+key
        self.content[key] = content

    def get(self, key, prefix="", **kwargs):
        key = prefix+key
        try:
            return self.content[key]
        except:
            if "default" in kwargs:
                return kwargs['default']
            else:
                raise CacheIndexException("No index in the cache called", key)

    def clear(self):
        self.content.clear()

class curry:
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs

        return self.fun(*(self.pending + args), **kw)

def get_cache(cache_obj, prefix):
    f_get = curry(cache_obj.get, prefix=prefix)
    f_set = curry(cache_obj.set, prefix=prefix)

    return f_get, f_set
