"""
Helper program to measure the cost of serializing

Different serializers are timed and the size of the serialized output is reported
"""

import random
import time
import sys
from contextlib import contextmanager

import cPickle
import pickle
import marshal


# Different objects to serialize
class A():
    def __init__(self):
        self.a = 1
        self.b = 2

d4 = ([A() for x in range(100)], "100 objects")

# Test objects and nice descriptions
i1 = (42, "a simple small int")
i2 = (sys.maxint, "a really big int")

l1 = (range(10), "a small int list")
l2 = (range(10000), "a large int list")

# classify objects
smalldata = [i1, i2, l1]
bigdata = [l2]
# proper repetition factors
small = 100
big = 1
# scale it
smalldata = [(a,b,small) for (a,b) in smalldata]
bigdata = [(a,b,big) for (a,b) in bigdata]


@contextmanager
def timing(printstr="time", repetitions=0, swallow_exception=True):
    start = time.time()
    try:
        yield
    except Exception, e:
        print "ERROR: " + str(e)
        if not swallow_exception:
            raise
    finally:
        total_time = time.time() - start
        if repetitions > 0:
            avg_time = total_time / repetitions
            print "%s: %f / %f sec." % (printstr, total_time, avg_time)
        else:
            print "%s: %f sec." % (printstr, total_time)


def runner(r = 100):
    # Serializers to try
    pickle_methods = [pickle, marshal, cPickle]

    for serializer in pickle_methods:
        for data, desc, scale in smalldata+bigdata:
            repetitions = r * scale
            with timing("%s dump+load reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                for i in xrange(repetitions):
                    s = serializer.dumps(data)
                    l = serializer.loads(s)


runner()


