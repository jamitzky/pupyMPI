"""
Helper program to measure the size of serialized data

Different serializers are timed with different datatypes
Also the serialization and unserialization methods are validated by checking that data is the same
"""

import sys

import cPickle
import pickle
import marshal

import numpy



# sequence sizes
small = 10
medium = 500
large = 10000


# Different objects to serialize
class A():
    def __init__(self):
        self.a = 1
        self.b = 2

d4 = ([A() for x in range(100)], "100 objects")

# Test objects and nice descriptions
s1 = ('reference string', "a small ASCII string")



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
smalldata = [s1, i1, i2, sl1, ml1, ml2]
bigdata = [ll1, ll2]
numpydata = [na1,na2,na3,na4,na5]




def runner(testdata=numpydata):
    """
    NOTE: With numpy 1.5 where numpy arrays and bytearray are friends the bytearray method is tested also
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
        try:
            serializer_name = serializer.__name__
        except:
            serializer_name = serializer
            
        print "%s serializing" % serializer_name
            
        for data, desc in testdata:
            try:
                elements = len(data) # How many elements
            except TypeError: # ints and such do not respond well to len
                elements = 1
            
            # Serialize
            try:
                if syntax == 'dumpload':
                    s = serializer.dumps(data) # serialize
                    l = serializer.loads(s)  # unserialize to verify                
                elif syntax == 'funcall':
                    s = serializer(data)  # serialize
                    try:
                        t = data.dtype
                        l = numpy.frombuffer(s,dtype=t) # unserialize to verify
                    except Exception as e:                        
                        l = str(s)
                elif syntax == 'methodcall':
                        s = data.tostring() # serialize
                        t = data.dtype
                        l = numpy.frombuffer(s,dtype=t) # unserialize to verify
                else:
                    print "syntax error!"
                    continue
            except AttributeError, e:
                print " cannot serialize %s with %s - error:%s" % (desc, serializer_name, e)
                continue
            except MemoryError, e:
                print " memory error trying to serialize %s with %s error:%s" % (desc, serializer_name, e)
                continue
            except Exception, e:
                print " error for %s with %s - error:%s" % (serializer_name,desc,e)
                continue


            serialized_size = len(s)                
            print "%i bytes for %s elements (%.1f bytes/element) data was %s" % (serialized_size, elements, (serialized_size/float(elements)), desc)

            if not numpy.alltrue( l == data ):
                print "...but unserialization with %s does not work for %s" % (serializer_name, desc)
                
        print "-"*40

# do it
#runner()
#runner(smalldata)
runner(smalldata+bigdata+numpydata)


