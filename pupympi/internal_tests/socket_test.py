"""
socket_test.py

Testing socket performance

NOTE:
We want to test several angles actually
Python platform:
- Python 3 vs. 2.6,2.7
- maybe IronPython, or others

methods:
- threaded socket connection
- multiprocessing connection

datastructures:
- stringbuffer, bytearray, array, numpy array, string, ctypes struct, struct

message size:
tiny = 1 byte
small = 32 bytes
medium = 1024 bytes
large = 4096
huge = 50 K

ISSUES:
Need some verification that what is sent is correctly received.
Need clean up
Need to test multiprocessing also

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

# generate a chunk of random data
def testdata(size):
    d = []
    alphabet = [chr(c) for c in xrange(256)]
    while size > 0:
        d.append(random.choice(alphabet))
        size -= 1
    return "".join(d)
    
def random_bytes(size):
    return "".join(chr(random.randrange(0, 256)) for i in xrange(size))


### STRINGS

def str_receiver(address,port):
    t0 = time.time()    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "string server setup"    
    conn, addr = s.accept()    
    print "string server connected"
    t1 = time.time()    

    more = True
    data = ""

    t2 = time.time()

    while more:
        r = conn.recv(1024)
        #print "server received, len",len(r)
        #print "r:",r
        if len(r) == 0:
            more = False
        else:
            data += r
    
    t3 = time.time()
    t = t2-t1
    print "string server done in %f seconds" % (t3-t2)
    #print "Data:",data
    conn.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)
    
def str_sender(address,port,times=100,size=50):
    t0 = time.time()    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((address,port))
    print "string sender connected"
    
    t1 = time.time()    
    data = testdata(size*times)
    i = 0
    
    t2 = time.time()    
    while times > i:
        s.send(data[i*size:(i+1)*size])
        i += 1
    
    t3 = time.time()
    print "string sender done in %f seconds" % (t3-t2)
    s.close()    
    t4 = time.time()
    return (t0,t1,t2,t3,t4)   
    
### STRUCTS    

def struct_receiver(address,port, times=100,size=50):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "struct server setup"    
    conn, addr = s.accept()    
    print "struct server connected"
    
    t1 = time.time()    
    data = getMessageStruct(size)

    t2 = time.time()
    while times > 0:
        conn.recv_into(data)
        times -= 1
    
    t3 = time.time()
    print "struct server done in %f seconds, data.content:" % (t3-t2)
    conn.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)


# Send a struct of max 50 bytes size many times
def struct_sender(address,port,times=100,size=50):
    connected = False
    while not connected:
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((address,port))
        except IOError as err:
            print "Connection error:",str(err)
            time.sleep(2)
            continue
        
        connected = True
    print "struct sender connected"
    
    t1 = time.time()
    # allocate struct
    data = getMessageStruct(size)    
    # Get size random bytes
    rbuffer = ctypes.create_string_buffer(testdata(times*size-1))
    i = 0
    
    t2 = time.time()
    while times > i:
        s.send(data)                  #  Send across a socket
        # Copy bytes into message content
        ctypes.memmove(data.content,rbuffer,size)            
        i += 1

    t3 = time.time()    
    print "struct sender done in %f seconds" % (t3-t2)
    s.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)

### BUFFER

def buffer_receiver(address,port, times=100, size=50):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "buffer server setup"    
    conn, addr = s.accept()    
    print "buffer server connected"
    
    t1 = time.time()
    data = ctypes.create_string_buffer(size)
    i = 0
    more = True
    
    t2 = time.time()
    while times > i or more:
        #conn.recv_into(data)
        (nbytes, address) = conn.recvfrom_into(data)
        if nbytes == 0:
            print "zeroth i:%i" %i
            more = False
        i += 1
            
    t3 = time.time()
    conn.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)


# Send a buffer of max 50 bytes size many times
def buffer_sender(address,port,times=100,size=50):
    connected = False
    while not connected:
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((address,port))
        except IOError as err:
            print "Connection error:",str(err)
            time.sleep(2)
            continue
        
        connected = True

    print "buffer sender connected"
    
    t1 = time.time()
    randstr = testdata(times*size)
    data = ctypes.create_string_buffer(randstr)
    i = 0
    
    t2 = time.time()
    while times > i:        
        s.send(data[i*size:(i+1)*size])                  #  Send across a socket
        i += 1

    t3 = time.time()
    print "buffer sender done in %f seconds" % (t3-t2)    
    s.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)


### ARRAY
    
def array_receiver(address,port, times=100, size=50):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "array server setup"    
    conn, addr = s.accept()    
    print "array server connected"
    
    t1 = time.time()
    data = array.array('B') # unsigned char array
    
    remain = size*times
    
    t2 = time.time()
    #conn.recv_into(data)
    while remain > 0:
        #data = conn.recv(size)
        data = conn.recv(min(remain,4096))
        remain -= len(data)
        print "received:%i - remain:%i" %(len(data),remain)
        #conn.recv_into(data)
        #(nbytes, address) = conn.recvfrom_into(data)
        #if nbytes == 0:
        #    #print "zeroth i:%i" %i
        #    more = False
        #else:
        #    print "Data:",data
        #    i += 1
            
    t3 = time.time()
    conn.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)


# Send a buffer of max 50 bytes size many times
def array_sender(address,port,times=100,size=50):
    connected = False
    while not connected:
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((address,port))
        except IOError as err:
            print "Connection error:",str(err)
            time.sleep(2)
            continue
        
        connected = True

    print "array sender connected"
    
    t1 = time.time()
    randstr = testdata(times*size)
    data = array.array('B',randstr)
    i = 0
    
    t2 = time.time()
    #s.send(data[i*size:(i+1)*size])
    while times > i:        
        #print "Now sending:",data[i*size:(i+1)*size]
        s.send(data[i*size:(i+1)*size])                  #  Send across a socket
        i += 1

    t3 = time.time()
    print "array sender done in %f seconds" % (t3-t2)    
    s.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)

### BYTEARRAY
    
def bytearray_receiver(address,port, times=100, size=50):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "bytearray server setup"    
    conn, addr = s.accept()    
    print "bytearray server connected"
    
    t1 = time.time()
    data = bytearray(size)
    i = 0
    more = True
    
    t2 = time.time()
    while times > i or more:
        #conn.recv_into(data)
        (nbytes, address) = conn.recvfrom_into(data)
        if nbytes == 0:
            print "zeroth i:%i" %i
            more = False
        i += 1
            
    t3 = time.time()
    conn.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)


# Send a buffer of max 50 bytes size many times
def bytearray_sender(address,port,times=100,size=50):
    connected = False
    while not connected:
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((address,port))
        except IOError as err:
            print "Connection error:",str(err)
            time.sleep(2)
            continue
        
        connected = True

    print "bytearray sender connected"
    
    t1 = time.time()
    randstr = testdata(times*size)
    data = bytearray(randstr)
    i = 0
    
    t2 = time.time()
    while times > i:        
        s.send(data[i*size:(i+1)*size])                  #  Send across a socket
        i += 1

    t3 = time.time()
    print "bytearray sender done in %f seconds" % (t3-t2)    
    s.close()
    t4 = time.time()
    return (t0,t1,t2,t3,t4)
    
    
    
### STARTER

def starter():
    port = 2525
    address = "localhost"
    times = 1000
    size = 50
    server = False
    struct = False
    buffer = False
    array = False
    byte = False
    all = False
    sleeptime = 3
    global message_size
    message_size = size
    
    """            
        struct sender done in 0.041831 seconds
        struct server done in 8.417099 seconds
        
        
    """
    for arg in sys.argv:
        if arg == "server":
            server = True
        if arg == "struct":
            struct = True
        if arg == "buffer":
            buffer = True
        if arg == "array":
            array = True
        if arg == "byte":
            byte = True
        if arg == "all":
            all = True
        elif arg.find("port:") > -1:
            l = arg.split(':')
    if struct:
        if server:
            (t0,t1,t2,t3,t4) = struct_receiver(address,port+1,times,size)
        else:
            (t0,t1,t2,t3,t4) = struct_sender(address,port+1,times,size)
        print "looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
    elif buffer:
        if server:
            (t0,t1,t2,t3,t4) = buffer_receiver(address,port+2,times,size)
        else:
            (t0,t1,t2,t3,t4) = buffer_sender(address,port+2,times,size)
        print "looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
    elif array:
        if server:
            (t0,t1,t2,t3,t4) = array_receiver(address,port+2,times,size)
        else:
            (t0,t1,t2,t3,t4) = array_sender(address,port+2,times,size)
        print "looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
    elif byte:
        if server:
            (t0,t1,t2,t3,t4) = bytearray_receiver(address,port+2,times,size)
        else:
            (t0,t1,t2,t3,t4) = bytearray_sender(address,port+2,times,size)
        print "looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
    elif all:
        if server:
            (t0,t1,t2,t3,t4) = str_receiver(address,port+3)
            print "string receiver - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
            (t0,t1,t2,t3,t4) = struct_receiver(address,port+2,times,size)
            print "struct receiver - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
            time.sleep(sleeptime)
            (t0,t1,t2,t3,t4) = buffer_receiver(address,port+1,times,size)
            print "buffer receiver - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
        else:
            (t0,t1,t2,t3,t4) = str_sender(address,port+3,times,size)
            print "string sender - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
            (t0,t1,t2,t3,t4) = struct_sender(address,port+2,times,size)
            print "struct sender - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
            time.sleep(sleeptime)
            (t0,t1,t2,t3,t4) = buffer_sender(address,port+1,times,size)
            print "buffer sender - looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
    else:
        if server:
            (t0,t1,t2,t3,t4) = str_receiver(address,port)
        else:
            (t0,t1,t2,t3,t4) = str_sender(address,port,times,size)
        print "looptime (t3-t2):%.4f data setup (t2-t1):%.4f connection setup (t1-t0):%.4f total (t4-t0):%.4f" % ((t3-t2),(t2-t1),(t1-t0),(t4-t0))
            
    
def tester():
    data = Message500()
    
    size = 12
    # Make a ctypes bytearray
    cbytes12 = ctypes.c_ubyte * size
    
    #cbytes12(87,86,85,127,128,601,4,4,4,4,5)
    bytes = ctypes.c_ubyte * size
    rbuffer = ctypes.create_string_buffer(testdata(size-1))
    sbuffer = ctypes.create_string_buffer("aabbccddeeffgghhiijjkkllmmnnooppqqrr")
    
    #print "rbuffer len:%i sizo:%i" % (len(rbuffer), ctypes.sizeof(rbuffer))
    #print "sbuffer len:%i sizo:%i" % (len(sbuffer), ctypes.sizeof(sbuffer))
    
    #ctypes.memmove(data.content,sbuffer[::2],size) # every other
    #ctypes.memmove(data.content,sbuffer[4:7],size) # funky result
    
    #for
    #bytestring = testdata(3)
    #data.content = cbytes12(bytestring)
    #data.content = rbuffer
        
    #print "Data.content:"
    #print data.content
    #for b in data.content:
    #    print b

    #print "sbuffer:"
    #print sbuffer
    #for c in sbuffer:
    #    print c
    
    #b1 = ctypes.c_byte(ord('c'))
    #b2 = ctypes.c_byte(ord('c'))
    #b3 = ctypes.c_char(chr(255))
    #print "b3.value",b3.value
    #print "b1",b1
    #print "b2",b2
    #print b1 == b2
    #print b1.value == b2.value
    t = 16
    size = 8
    d = range(t*size)
    print d
    
    while t > 0:
        t -= 1
        print d[t*size:t*size+size]
    

### Testing grounds
#tester()
#starter()
import os, sys
def execution_path(filename):
    return os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), filename)

print "curwd:", os.getcwd()
print "__file__:", __file__
print "argv:",sys.argv

ptcf = os.path.join(os.getcwd(),sys.argv[0])
p,rest = os.path.split(ptcf)
ptcf1u = os.path.split(p)
print "cur+argv:",ptcf
print "cur+argv-1up:",ptcf1u

#fp = __file__
#import os
#print os.path.dirname(__file__)

text = "somestring"
#for c in text:
    #print c
#b = bytearray([65, 66, 67])
#b = bytearray(testdata(50))
#print b

