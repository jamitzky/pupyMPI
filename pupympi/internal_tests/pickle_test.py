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

small = 10
medium = 500
large = 10000

na1 = (numpy.array(range(small), dtype='int64'), "a small(%i) numpy int64 array" % small)
na2 = (numpy.array(range(medium), dtype='int64'), "a medium(%i) numpy int64 array" % medium)
na3 = (numpy.array(range(medium),dtype='float64'), "a medium(%i) numpy float64 array" % medium)
na4 = (numpy.array(range(large),dtype='int64'), "a large(%i) numpy int64 array" % large)
na5 = (numpy.array(range(large),dtype='float64'), "a large(%i) numpy float64 array" % large)

# classify objects
smalldata = [i1, i2, l1]
bigdata = [l2]
numpydata = [na1,na2,na3,na4,na5]

# proper repetition factors
manyreps = 100
fewreps = 1
# scale it
smalldata = [(a,b,manyreps) for (a,b) in smalldata]
bigdata = [(a,b,fewreps) for (a,b) in bigdata]

numpydata =  [(a,b,fewreps) for (a,b) in numpydata]

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


def plainrunner(r = 100, testdata=smalldata+bigdata):
    """
    Works on all types
    """
    # Serializers to try
    pickle_methods = [pickle, marshal, cPickle]

    for serializer in pickle_methods:
        for data, desc, scale in testdata:
            repetitions = r * scale
            with timing("%s dump+load reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                for i in xrange(repetitions):
                    s = serializer.dumps(data)
                    l = serializer.loads(s)
                
        print "-"*40


def numpyrunner(r = 100, testdata=numpydata):
    """
    Only works on types supporting bytearray and .tostring (ie. numpy arrays)
    
    NOTE: Made to run with numpy 1.5 where numpy arrays and bytearray are friends
    """   
    # Serializers to try along with call hint
    serializer_methods =    [(pickle,'dumpload',),
                            (cPickle,'dumpload'),
                            (marshal,'dumpload'),
                            ('tostring','methodcall'),
                            ]
    
    # For numpy versions before 1.5 bytearray cannot take multi-byte numpy arrays so skip that method
    if numpy.__version__ >= '1.5':
        serializer_methods.append( (bytearray,'funcall') )

    for (serializer,syntax) in serializer_methods:
        for data, desc, scale in testdata:
            repetitions = r * scale
            if syntax == 'dumpload':
                with timing("%s dump+load reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                    for i in xrange(repetitions):
                        s = serializer.dumps(data)
                        l = serializer.loads(s)
                        
            elif syntax == 'funcall':
                # The received data will be in the form of a string so we convert beforehand
                s2 = str(serializer(data))
                with timing("%s func+frombuffer reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                    # TODO: Include this in timing or not?
                    t = data.dtype
                    for i in xrange(repetitions):
                        s = serializer(data)
                        l = numpy.frombuffer(s2,dtype=t)

                # The received data will be in the form of a string so we convert beforehand
                s2 = str(serializer(data))
                with timing("%s func+fromstring reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                    # TODO: Include this in timing or not?
                    t = data.dtype
                    for i in xrange(repetitions):
                        s = serializer(data)
                        l = numpy.fromstring(s2,dtype=t)
            
            # This case is a bit different
            elif syntax == 'methodcall':
                with timing("%s methodcall+fromstring reps:%i %s" % ('tostring', repetitions,desc),repetitions):
                    # TODO: Include this in timing or not?
                    t = data.dtype
                    for i in xrange(repetitions):
                        s = data.tostring()
                        l = numpy.fromstring(s,dtype=t)

                with timing("%s methodcall+frombuffer reps:%i %s" % ('tostring', repetitions,desc),repetitions):
                    # TODO: Include this in timing or not?
                    t = data.dtype
                    for i in xrange(repetitions):
                        s = data.tostring()
                        l = numpy.frombuffer(s,dtype=t)
            else:
                print "syntax error!"
                
        print "-"*40

# do it
#plainrunner()
numpyrunner(100)


