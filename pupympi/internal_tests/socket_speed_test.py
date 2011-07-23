import threading
import os
import time
import tempfile
import socket
import random
import string
import sys
import numpy
import optparse

"""
This module is for benchmarking different methods of sending data over Python
sockets.

The costs of setting up and tearing down the connection are not counted, as this
should be the same for all methods. The cost of validating the correctness is
not counted either since this is just for ensuring correctness during development.

NOTES:

- For now we test with a sink or with a message size known to both sides. This is intentional
  since we want to measure only the simplest recv and send loops. In the
  practical applications we need to have the header received examined before
  receiving the payload but this makes measuring more complicated and also
  depends on eg. the header format chosen. So we postpone this.
  
QUESTIONS:
- it seems that when sending, all the bytes are sent every time no matter how many are passed to socket.send
  This means that advice on how to construct the send loop is largely meaningless since there is never any looping done
  This finding leads to two questions:
  1) Why does socket send never return with a sent amount less than the full - as the docs state it could?
     Maybe we have some sort of setting that inhibit it?
  2) Is it fine that socket send is busy for the whole sending period? Or would we benefit from
     sending in smaller batches?
     Is the call releasing the GIL?
     What is the effect when multiple processes send over the same network interface? Will there be queuing up or intermingling?
     Do we use too much memory?
     
     
  
ISSUES:
- When running multiple functions under one conf, prebuf can conflict with validation and type may conflict too
- Pregenerated data should only be generated once for each requested type, and of maximum size (confs needing less can slice)
- Turn off delayed ack/nagle for connections
- Validation of conf should include python version
- Occasionally the port is not freed before attempting next connection setup, maybe sleep between, or increment port number for each conf
- when using unixsockets the user has to manually paste the filename, instead an agreed upon filename should be used





FINDINGS:

SOCKET.SEND only returns before sending everything in the case of
1) non-blocking socket
and
2) message too large to fit in buffer but not too large for buffer not to
   have cleared out on next go-around in the loop

GENERAL THROUGPUT BASED ON SENDBUFFER SIZE
testing on klynge sending from n1 to n0
sending 10**7 bytes
to a receiver getting chunks of 1024 bytes
maximum is 1024*128 ( which is reported as double =262142)

unset buffer: 120000-125000 kB/s (which means default of 8K)
128K-64K  buffer: 115000
32K: 114000
16K: 110000 (here naive sender is slightly faster)
8K: 79000
4K: 77000 (again naive is slightly faster)
2K: 77000
1K: 1600 (rock bottom performance)

"""


### AUXILLARY


def generate_container(type,size,filler=0):
    """
    Generate a container representing a buffer preallocated by the user
    
    Size is the size in bytes of the container.
    Filler is the value of the filler elements.
    """
    if type == 'numpy':
        # We assume a standard int size of 64 bit
        intsize = 8
        elements = size // intsize
        container = numpy.array([filler]*elements)
    elif type == 'bytearray':
        container = bytearray([filler]*size)
    else:
        raise Exception("unknown container type requested")
        
    return container

def generate_data(confs):
    """
    Generate the required amount of testdata for each configuration
    
    ISSUE:
    - Could do with prettier type determination
    - need numpy floats and perhaps other integer/string types
    """
    # We like predictable random for testing
    random.seed(42)
    numpy.random.seed(42)
    
    
    for conf in confs:
        size = conf['msgsize']
        print("generating data size:%i of type:%s" % (size, conf['msgtype']) )
        if conf['msgtype'] == 'ascii':
            # only lowercase chars from alphabet
            conf['data'] = ''.join(random.choice(string.ascii_lowercase) for i in xrange(size))
            
        elif conf['msgtype'] == 'numpy':
            elementsize = 8 # 8 bytes per numpy array element as standard
            conf['data'] = numpy.random.random_integers(0,size//elementsize,size//elementsize )  # numpy random
            
        elif conf['msgtype'] == 'bytearray':
            size = conf['msgsize']
            # TODO: make more random
            bytestring = ''.join([ chr(i%255) for i in xrange(size) ])
            try:
                conf['data'] = bytearray(bytestring)
            except TypeError as e:        
                conf['data'] = bytearray(bytestring.encode('latin-1')) # Python 3 needs special treatment
            
        else:
            print("Bad type")
            
def validate_conf(conf):
    """
    check that configuration is valid
    
    TODO:
    - Type vs. recv function
    - Type vs. send function
    - Python version vs. recv function
    - Python version vs. send function        
    """
    valid = True
    try:
        msgtype = conf['msgtype']
        msgsize = conf['msgsize']
        iterations = conf['iterations']
        sfunctions = conf['sfunctions']
        rfunctions = conf['rfunctions']
        address = conf['address']
        port = conf['port']
    except Exception as e:
        print("Bad configuration - one or more keys missing")
        return False

    # Check that types of more than 1 byte have proper bytesize
    if msgtype == 'numpy':
        if 0 != msgsize % 8:
            print("Invalid configuration, msgsize needs to be divisible by the bytesize of msgtype")
            valid = False
    
    return valid

def validate_results(received_data_list,reference_data):
    """
    simple check that all elements of received_data are equal to reference_data
    
    only the first non-match is printed
    """
    for data in received_data_list:
        if numpy.alltrue(data != reference_data): # This works fine for bytearrays also            
            toomuch = 100 # For big comparisons it makes no sense to spew everything to stdout
            size = len(data)
            refsize = len(reference_data)
            if size > toomuch or refsize > toomuch:
                if size != refsize:
                    print( "INVALID\nreceived data length:%s does not equal the reference data length:%s" % (size,refsize) )
                    return False
                else:
                    print( "INVALID\n spooky ... lengths check out (%i and %i)" % (size,refsize) )
                    for i,element in enumerate(reference_data):
                        if element != data[i]:
                            print("\t comparison differs at index:%i received:%s vs. ref:%s" % (i,data[i:i+5],reference_data[i:i+5]))
                            return False
            else:
                print("INVALID\n%s\ndoes not equal the reference:\n%s" % (data,reference_data))
                # DEBUG
                #for i,x in enumerate(data):
                #    print("data[%i]:%s vs. ref:%s" % (i, x, reference_data[i]) )
            return False
    return True


### SEND LOOPS

def str_primitive_send(connection,msg,verbose=False):
    """
    Meant to be called on blocking sockets
    """
    loopcount = 0
    size = len(msg)
    sent = 0
    while sent < size:
        sent += connection.send(msg[sent:])
        loopcount += 1
        print("Sender SENT:%i" % sent)
    if verbose:
        print("Sender looped %i times" % loopcount)


def str_primitive_send_nb(connection,msg,verbose=False):
    """
    Robust enough for non-blocking sockets
    """
    loopcount = 0
    size = len(msg)
    sent = 0
    while sent < size:
        try:
            sent += connection.send(msg[sent:])
        except socket.error as e:
            print "ouch got:%s" % e
        loopcount += 1
    if verbose:
        print("Sender looped %i times" % loopcount)
        
def str_buffer_send(connection,msg,verbose=False):
    """    
    Defunct in python 3 where buffer is replaced by memoryview
    """
    loopcount = 0
    buf = buffer(msg)
    while len(buf):
        buf = buffer(msg,len(buf) + connection.send(buf))
        loopcount += 1
    
    if verbose:
        print("Sender looped %i times" % loopcount)

def str_buffer_send_nb(connection,msg,verbose=False):
    """
    Robust enough for non-blocking sockets
    
    Defunct in python 3 where buffer is replaced by memoryview
    """
    loopcount = 0
    buf = buffer(msg)
    while len(buf):
        try:
            s = connection.send(buf)
            buf = buffer(msg,len(buf) + s)
        except socket.error as e:
            print "ouch got:%s" % e

        loopcount += 1    
    if verbose:
        print("Sender looped %i times" % loopcount)

def str_view_send(connection,msg,verbose=False):
    """
    Works for both 2.7 and 3.1
    """
    loopcount = 0
    bytesize = len(msg)
    sent = 0
    view = memoryview(msg.encode('latin1'))
    while sent < bytesize:        
        sent += connection.send(view[sent:])
        loopcount += 1
    
    if verbose:
        print("Sender looped %i times" % loopcount)


def numpy_send(connection,msg):
    """
    for now this is the same as primitive send, but we should determine whether
    time is saved by using a view over the numpy array in the loop instead of normal slice
    """
    loopcount = 0
    bytesize = msg.nbytes
    sent = 0
    while sent < bytesize:
        sent += connection.send(msg[sent:])
        loopcount += 1
    
    if verbose:
        print("Sender looped %i times" % loopcount)
    # DEBUG
    #print("sent a numpy array of %i type:%s element-type:%s" % (len(msg),type(msg),type(msg[0])))

        
def bytearray_send(connection,msg,verbose=False):
    loopcount = 0
    bytesize = len(msg) # len equals size for bytearrays
    sent = 0
    view = memoryview(msg)
    while sent < bytesize:
        sent += connection.send(view[sent:])
        loopcount += 1
    
    if verbose:
        print("Sender looped %i times" % loopcount)


### RECEIVE LOOPS

def str_primitive_recv(connection,size,dummyarg=None):
    """
    Breaks for 3.1
    """
    received = ""
    missing = size
    while missing:
        try:
            #received += connection.recv(missing)
            received += connection.recv(min(missing,4096))
            missing = size- len(received)
        except Exception as e:
            print("Receiver error:%s" % e)
            raise e
    
    return received

def str_decoding_recv(connection,size,dummyarg=None):    
    """
    Works for both 2.7 and 3.1
    """
    received = b''
    missing = size
    while missing:
        try:
            received += connection.recv(missing)
            missing = size- len(received)
        except Exception as e:
            print("Receiver error:%s" % e)
            raise e
    
    return received.decode('latin1')
    
def str_list_recv(connection,size,dummyarg=None):
    """
    Trying to reduce string appends this way does not seem to help much. Only
    when rigging the test to loop a lot (ie. for very large message sizes) will
    this method _sometimes_ win over the primitive receive.
    
    I guess the problem is we have to allocate the chunk explicitly in every
    iteration since we need to check its length. Maybe Pythonistas recommend this
    for historic reasons, since string concat used to be very slow.
    """
    received = []
    missing = size
    while missing:
        try:
            #chunk = connection.recv(missing)
            chunk = connection.recv(min(missing,4096))
            missing -= len(chunk)
            received.append(chunk)
        except Exception as e:
            print("Receiver error:%s" % e)
            
    return ''.join(received)


def numpy_recv(connection,size,container=None):
    intsize = 8 # standard int when converted to numpy int (on 64 bit python build)
    
    if container is None:
        container = generate_container('numpy',size)
    
    view = memoryview(container)
    missing = size
    while missing:
        try:
            #print("Receiver - size:%i, missing:%i, viewsize:%i" % (size,missing,len(view[size-missing:].tobytes())))
            #received = connection.recv_into(view[(size-missing)//intsize:],missing) # striding in view is of element-size
            #missing -= received
            missing -= connection.recv_into(view[(size-missing)//intsize:],missing) # striding in view is of element-size
        except ValueError as e:
            raise e
    
    return container
    

def bytearray_recv(connection,size,container=None):
    if container is None:
        container = bytearray(size) # pre-allocate
        
    view = memoryview(container)
    missing = size
    while missing:
        try:
            missing -= connection.recv_into(view[size-missing:],missing)
        except Exception as e:
            print("Receiver error:%s" % e)
    
    return container


### MISSION CONTROL
def sender(confs):
    def setup_connection(portno,address):
        maxtries = 3
        tries = 1
        while tries < maxtries:
            print("Sender trying port:%i try:%i" % (portno,tries))
            try:
                if conf['connection_type'] == "local":
                    print("Creating local socket to file %s" % (conf['socketfile']))
                    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client_socket.connect(conf['socketfile'])
            
                elif conf['connection_type'] == "tcp":
                    print("Creating TCP socket to (%s, %s)" % (portno,address))
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
                    #client_socket.setblocking(1)
                    #client_socket.settimeout(0.5)
                    #client_socket.settimeout(0.0)
                    #client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,1024*8) # standard size is 1024*8
                    bufs = client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                    nodelay = client_socket.getsockopt(socket.SOL_TCP, socket.TCP_NODELAY)
                    client_socket.connect( (address, portno))
                    client_socket.settimeout(0.0) # set it to blocking AFTER connecting to avoid "[Errno 115] Operation now in progress"
                    print("Connected TCP socket SO_SNDBUF:%i TCP_NODELAY:%i timeout:%s" % (bufs, nodelay, client_socket.gettimeout()) )
            except socket.error as e:
                print "got a socket error (%s) trying again..." % e
                tries += 1
                time.sleep(tries) # give receiver time to open listening socket

            return client_socket

    
    # Run configurations that are to be tested
    for conf in confs:
        if not validate_conf(conf):
            continue
        
        if conf['connection_type'] == 'local':
            socketfile = raw_input("paste name of socketfile:")        
            conf['socketfile'] = socketfile
            
        functions = conf['sfunctions']
        msg = conf['data']
        iterations = conf['iterations']
        size = conf['msgsize']
        
        for func in functions:
            connection = setup_connection(conf['port'],conf['address'])
            ## DEBUG
            #print("Sender sending %s" % msg)
            
            t1 = time.time()        
            for i in xrange(conf['iterations']):
                func(connection, msg, conf['verbose'])
            t2 = time.time()
            
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            
            print("(%i kB/s) -- %s -- sent %i times %i bytes(*) in %f seconds" % ((iterations*size)/(1024*(t2-t1)), func.__name__,iterations,size,t2-t1) ) 


def receiver(confs):
    def setup_connection(portno,address):
        if conf['connection_type'] == "local":
            socketfile = raw_input("paste name of socketfile:")
            #socketfile = tempfile.NamedTemporaryFile()
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_socket.bind(socketfile)
    
        elif conf['connection_type'] == "tcp":            
            unbound = True
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            while unbound:
                try:
                    server_socket.bind( (address, portno) )
                    unbound = False
                except socket.error as e:    
                    #raise e
                    portno += 1
                    print("port not available (error:%s), trying %i ..." % (e,portno) )           
                except Exception as e:
                    print("unexpected error:%s" % e )
                    raise e
                
            server_socket.listen(10)
            
        print("Receiver listening on port no:%i" % portno)
        
        return server_socket.accept()
       
    # Run configurations that are to be tested
    for conf in confs:
        if not validate_conf(conf):
            print("ignored invalid conf! %s" % conf)
            continue
        
        functions = conf['rfunctions']
        size = conf['msgsize']
        iterations = conf['iterations']
        msgtype = conf['msgtype']
        prebuf = conf.get('prebuf',False)
        
        # pregenerate a container if buffer-reuse is in effect
        if prebuf:
            container = generate_container(msgtype,size)
        else:
            container = None
            
        for func in functions:
            connection, address = setup_connection(conf['port'],conf['address'])
            print("Receiver accepted connection")
            
            # DEBUG
            #print("C0: %s" % container)
            
            if prebuf:
                t1 = time.time()
                for i in xrange(iterations):                
                    # DEBUG
                    #print("C1: %s" % container)
                    func(connection, size, container)
                t2 = time.time()
            else:
                t1 = time.time()
                for i in xrange(iterations):
                    # DEBUG
                    #print("C1: %s" % container)
                    container = func(connection, size, container)                    
                t2 = time.time()
                
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            
            print("(%i kB/s) -- %s -- got %i times %i bytes(*) in %f seconds" % ((iterations*size)/(1024*(t2-t1)), func.__name__,iterations,size,t2-t1))
        

def sink(confs):
    def setup_connection(portno,address):
        if conf['connection_type'] == "local":
            global socketfile
            socketfile = tempfile.NamedTemporaryFile().name
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_socket.bind(socketfile)
            server_socket.listen(10)                
            print("Sink listening on file:%s" % (socketfile) )
    
        elif conf['connection_type'] == "tcp":            
            unbound = True
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rcvbuf = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
            while unbound:
                try:
                    server_socket.bind( (address, portno) )
                    unbound = False
                except socket.error as e:    
                    #raise e
                    portno += 1
                    print("port not available (error:%s), trying %i ..." % (e,portno) )           
                except Exception as e:
                    print("unexpected error:%s" % e )
                    raise e
                
            server_socket.listen(10)                
            print("Sink listening on host:%s port no:%i" % (address,portno) )
        
        return server_socket
    
    conf = confs[0]
    server_socket = setup_connection(conf['port'],conf['address'])
    buffersize = conf['buffersize']
    try:
        while True:
            total = 0
            max_received = 0
            connection, address = server_socket.accept()
            #address = server_socket.accept()
            print("Sink (chunksize:%i) accepted connection from %s" % (buffersize,address) )
            while True:
                try:
                    data = connection.recv(buffersize)
                    if data:
                        l = len(data)
                        total += l
                        if l == buffersize:
                            max_received += 1
                            #print "got datalen:%s \t%s" % (l, "" if l < buffersize else "!")
                    else:
                        print "sink got empty data (connection closed) after receiving %i bytes" % total
                        break
                except Exception as e:
                    print "inner loop got exception:%s" % e
                    break
                
            print("sink had %i receptions of max size, SO_RCVBUF:%i" % (max_received, server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)) )
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            
    except KeyboardInterrupt as e:
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
        print "sink stopped"
    

def runner():
    # Parse args
    parser = optparse.OptionParser()
    parser.add_option("-P", "--port", dest="port", default=15001, type=int,
                      help="which port to use")
    parser.add_option("-H", "--host", dest="host", default="127.0.0.1",
                      help="which host address to use")
    (options, args) = parser.parse_args()

    port = options.port
    host = options.host
    type = None
    if 's' in args or 'sender' in args:
        type = 'sender'
    elif 'r' in args or 'receiver' in args:
        type = 'receiver'
    else:
        type = 'sink'
    
    # Python 2.6 compatible
    testconf1 = {
        "verbose" : True,
        "iterations" : 4,
        "msgsize" : 10**6, # always in bytes
        "msgtype" : 'ascii',
        #"sfunctions" : [str_buffer_send],
        #"rfunctions" : [str_list_recv],
        "sfunctions" : [str_primitive_send_nb],
        "rfunctions" : [str_primitive_recv],
        #"sfunctions" : [str_primitive_send, str_primitive_send, str_buffer_send, str_buffer_send],
        #"rfunctions" : [str_primitive_recv, str_list_recv,str_primitive_recv, str_list_recv],
        #"sfunctions" : [str_primitive_send_nb, str_buffer_send_nb],
        #"rfunctions" : [str_primitive_recv, str_list_recv],
        "port" : port,  # This one should be pre-cleared
        "address" : host,
        #"connection_type" : 'local',
        "connection_type" : 'tcp',
        "buffersize" : 2**10, # Good ol' 1024
        #"buffersize" : 2**12, # Good ol' 4096
        #"buffersize" : 2**13, # 8192
        #"buffersize" : 2**14, # 16384
        #"buffersize" : 2**15, # 32768
        #"buffersize" : 2**16, # 65536
        #"buffersize" : 2**17, # 131072
        #"buffersize" : 2**18, # 262144
        #"buffersize" : 2**19, # 524288 (This size is possible via localhost)
        #"buffersize" : 2**20, # 1048576 (This size has not been observed even via localhost)
    }

    # Switcheroo
    configurations = [testconf1]
    
    # do it
    if type=='sender':
        generate_data(configurations) # pre-generate data to ensure that both ends have same set
        sender(configurations)
    elif type=='receiver':
        receiver(configurations)
    else:
        sink(configurations)
        
    print("done running %i configurations" % (len(configurations)))
    
runner()
