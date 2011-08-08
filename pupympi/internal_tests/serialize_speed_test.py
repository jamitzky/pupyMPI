"""
Helper program to measure the speed of serializing and unserializing

Different serializers are timed with different datatypes

ISSUES:
- The setup could be generated a lot nicer and more programmatically
- We should test the effect of GC
"""

import time
import sys
from contextlib import contextmanager

import cPickle
import pickle
import marshal

import numpy



# sequence sizes
small = 10
smallish = 100
medium = 500
big = 1000
bigger = 2000
large = 10000


# Different objects to serialize
class A():
    def __init__(self):
        self.a = 1
        self.b = 2

d4 = ([A() for x in range(100)], "100 objects")

# Test objects and nice descriptions

i1 = (42, "a simple small int")
i2 = (sys.maxint, "a really big int")

sl1 = (range(small), "a small(%i) int list" % small)

ml1 = (range(medium), "a medium(%i) int list" % medium)
ml2 = ([ i*1.0/3.0 for i in range(medium) ], "a medium(%i) float list" % medium)

ll1 = (range(large), "a large(%i) int list" % large)
ll2 = ([ i*1.0/3.0 for i in range(large) ], "a large(%i) float list" % large)

na1 = (numpy.array(range(small), dtype='int64'), "a small(%i) numpy int64 array" % small)
na2 = (numpy.array(range(medium), dtype='int64'), "a medium(%i) numpy int64 array" % medium)
na3 = (numpy.array(range(medium),dtype='float64'), "a medium(%i) numpy float64 array" % medium)
na4 = (numpy.array(range(large),dtype='int64'), "a large(%i) numpy int64 array" % large)
na5 = (numpy.array(range(large),dtype='float64'), "a large(%i) numpy float64 array" % large)

# classify objects
smalldata = [i1, i2, sl1, ml1, ml2]
bigdata = [ll1, ll2]
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
    pickle_methods = [pickle, cPickle, marshal]

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
    
    NOTE: With numpy 1.5 where numpy arrays and bytearray are friends the bytearray method is tested also
    """   
    # Serializers to try along with call hint and protocol version
    serializer_methods =    [
                            (pickle,'dumpload',pickle.HIGHEST_PROTOCOL),
                            (cPickle,'dumpload',cPickle.HIGHEST_PROTOCOL),
                            (marshal,'dumpload',2),
                            ('.tostring','methodcall',None),
                            ('.tostring b','methodcall',None),
                            ('.view','methodcall',None)
                            ]
    
    # For numpy versions before 1.5 bytearray cannot take multi-byte numpy arrays so skip that method
    if numpy.__version__ >= '1.5':
        serializer_methods.append( (bytearray,'funcall',None) )

    for (serializer,syntax,version) in serializer_methods:
        for data, desc, scale in testdata:
            repetitions = r * scale
            if syntax == 'dumpload':
                with timing("%s dump+load reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                    for i in xrange(repetitions):
                        s = serializer.dumps(data,version)
                        l = serializer.loads(s)
                        
            elif syntax == 'funcall':
                if type(data) == numpy.ndarray:
                    with timing("%s func+frombuffer reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):
                        for i in xrange(repetitions):
                            t = data.dtype                            
                            s = serializer(data)                        
                            l = numpy.frombuffer(s,dtype=t)
                elif isinstance(data, str):
                    with timing("%s func+str reps:%i %s" % (serializer.__name__, repetitions,desc),repetitions):                                                
                        for i in xrange(repetitions):
                            t = type(data)
                            s = serializer(data)
                            l = t(s)                                
                else:
                    print "%s ignoring type %s" % (serializer.__name__, type(data))
            
            # This case is a bit different
            elif syntax == 'methodcall':
                if type(data) == numpy.ndarray:
                    if serializer == '.tostring':
                        with timing("%s methodcall+fromstring reps:%i %s" % (serializer, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.tostring()
                                l = numpy.fromstring(s,dtype=t)
                    elif serializer == '.tostring b':
                        with timing("%s methodcall+frombuffer reps:%i %s" % (serializer, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.tostring()
                                l = numpy.frombuffer(s,dtype=t)
                    elif serializer == '.view':
                        # The received data will be in the form of a string so we convert beforehand
                        s2 = data.view(numpy.uint8).tostring()
                        with timing("%s methodcall+frombuffer reps:%i %s" % (serializer, repetitions,desc),repetitions):
                            for i in xrange(repetitions):
                                t = data.dtype
                                s = data.view(numpy.uint8)
                                l = numpy.frombuffer(s2,dtype=t)
                else:
                    print "ignoring type:%s since it has no tostring method" % type(data)                    

            else:
                print "syntax error!"
                
        print "-"*40

# do it
#plainrunner(100)
#plainrunner(1000, testdata=numpydata)

#numpyrunner(10)
numpyrunner(1000)
#numpyrunner(100, testdata=smalldata+bigdata)
#numpyrunner(100, testdata=numpydata)

