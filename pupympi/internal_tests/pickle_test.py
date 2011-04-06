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

import numpy

numpy_formats = {
    11 : {"type" : numpy.dtype('bool'), "bytesize" : 1, "description" : "Boolean (True or False) stored as a byte"},
    13 : {"type" : numpy.dtype('int8'), "bytesize" : 1, "description" : "Byte (-128 to 127)" },
    14 : {"type" : numpy.dtype('int16'), "bytesize" : 2, "description" : "Integer (-32768 to 32767)" },
    15 : {"type" : numpy.dtype('int32'), "bytesize" : 4, "description" : "Integer (-2147483648 to 2147483647)" },
    16 : {"type" : numpy.dtype('int64'), "bytesize" : 8, "description" : "Integer (9223372036854775808 to 9223372036854775807)" },
    17 : {"type" : numpy.dtype('uint8'), "bytesize" : 1, "description" : "Unsigned integer (0 to 255)" },
    18 : {"type" : numpy.dtype('uint16'), "bytesize" : 2, "description" : "Unsigned integer (0 to 65535)" },
    19 : {"type" : numpy.dtype('uint32'), "bytesize" : 4, "description" : "Unsigned integer (0 to 4294967295)" },
    20 : {"type" : numpy.dtype('uint64'), "bytesize" : 8, "description" : "Unsigned integer (0 to 18446744073709551615)" },
    23 : {"type" : numpy.dtype('float32'), "bytesize" : 4, "description" : "Single precision float: sign bit, 8 bits exponent, 23 bits mantissa" },
    24 : {"type" : numpy.dtype('float64'), "bytesize" : 8, "description" : "Double precision float: sign bit, 11 bits exponent, 52 bits mantissa" },
    26 : {"type" : numpy.dtype('complex64'), "bytesize" : 8, "description" : "Complex number, represented by two 32-bit floats (real and imaginary components)" },
    27 : {"type" : numpy.dtype('complex128'), "bytesize" : 16, "description" : "Complex number, represented by two 64-bit floats (real and imaginary components)" },
    # 30 is bytearray
    # 31 is ndarrays
}


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
                
        print "-"*40


runner()


