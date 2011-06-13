"""
socket_test.py

Testing socket performance

This program is for testing raw speed of different ways of transferring data in
and out of sockets in Python

The premise is that a user has put the data into one of the Python data
structures and needs it transferred over a socket to a different process
and back into the same type of datastructure.


datastructures:
- list, string, stringbuffer, bytearray, array, numpy array, struct, ctypes struct

message sizes:
tiny = 1 byte
small = 32 bytes
medium = 1024 bytes
large = 4096
huge = 50 K

"""
import sys
import random
import time
import timeit
import socket

import ctypes
import array

### AUXILLARY FUNCTIONS ###

class Point(ctypes.Structure):
    _fields_ = [ ('x',ctypes.c_double), ('y',ctypes.c_double), ('z',ctypes.c_double) ]

# Message struct with fixed size content buffer
class Message500(ctypes.Structure):    
    _fields_ = [ ('content',ctypes.c_ubyte * 500)]

# Just a wrapper for easier access to variable sized classes
def getMessageStruct(s):
    class Message(ctypes.Structure):    
        _fields_ = [ ('content',ctypes.c_ubyte * s)]
    return Message()

#formatstring = "initial:%.4f setup:%.4f loopstart:%.4f loopend:%.4f end:%.4f\nlooptime (t3-t2):%.4f total (t4-t0):%.4f" % (t0,t1,t2,t3,t4,(t3-t2),(t4-t0))

def random_cbytes(size):
    bytes = ctypes.c_ubyte * size
    #for b in xrange(size):
    #    bytes[b] = 11
    rbuffer = ctypes.create_string_buffer(testdata(size))
    ctypes.memmove(bytes,rbuffer,size)
    
    return bytes

def random_bytes(size):
    random.seed(42) # best kind of random is the one you can predict...
    return "".join(chr(random.randrange(0, 256)) for i in xrange(size))


# generate a chunk of random data
def testdata(size, seed = 42):
    random.seed(seed) # best kind of random is the one you can predict...
    d = []
    
    alphabet = [chr(c) for c in xrange(256)] # Generate an alphabet to choose from    
    while size > 0:
        d.append(random.choice(alphabet))
        size -= 1
    return "".join(d)
    


### MAIN FUNCTIONS

def starter():
    # Check predictability of randomness
    print "--- starting ----"
    size = 8
    rbytes = random_bytes(size)
    rtestdata = testdata(size)
    rcbytest = random_cbytes(size)
    
    
    print "--- done ----"
    
    
    
### Testing grounds
starter()
