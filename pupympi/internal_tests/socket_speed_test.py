import threading
import os
import time
import tempfile
import copy
import socket
import random
import string
import platform
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
- Allow minimum python version in conf and validation of conf should include python version
- Allow signaling that a conf wants a freshly made socket connection (to test with tcp slow start etc.)
- consolidate printing of essential benchmark info, should be done after running a conf based on conf data
- still not Python3 compatible

FINDINGS:

SOCKET.SEND only returns before sending everything in the case of
1) non-blocking socket
and
2) message too large to fit in buffer but not too large for buffer not to
   have cleared out on next go-around in the loop

GENERAL THROUGPUT BASED ON SENDBUFFER SIZE
using the str_primitive_send and str_buffer_send
using blocking sockets
testing on klynge sending from n1 to n0
sending 10**7 bytes
to a receiver getting chunks of 1024 bytes
maximum is 1024*128 ( which is reported as double =262142)

unset buffer: 120000-125000 kB/s (which means default of 8K)
128K-64K  buffer: 115000
32K: 114000
16K: 110000 (here primitive sender is slightly faster)
8K: 79000
4K: 77000 (again primitive is slightly faster)
2K: 77000
1K: 1600 (rock bottom performance)


HIGHER THROUGPUT WITH NON-BLOCKING SOCKETS
using the str_primitive_send_nb and str_buffer_send_nb
using non-blocking sockets
testing on klynge sending from n1 to n0
sending 10**6 bytes
to a receiver getting chunks of 1024 bytes

Seems like speed is exceptionally fast when sending 6 times 10**6 bytes.
This might be an issue with lucky buffers or something since when using 2 times 10**6
or 10**7 or coming after a function that did something, the speed cannot be reproduced.

unset buffer: 280000-300000 kB/s (!)
With sndbuf specified, the results are more or less the same as with blocking sockets
"""

### VERSION JIGGLING
version = tuple(map(int, platform.python_version_tuple()[:-1] ) )


if version[0] > 2:
    # No xrange for python 3
    xrange = range

### AUXILLARY
possible_conf_keys = [
                      'process_type',       # sender, receiver, faucet or sink
                      'python_version',     # 2.6,2.7,3.1,3.2
                      'msg_size',
                      'msg_type',           # ascii, bytearray, numpy
                      'iterations',         # how many times msg is sent
                      'send_function',
                      'recv_function',
                      'port',               # listening port on receiving end (invalid for unixsockets)
                      'host',               # host address on receiving end (invalid for unixsockets)
                      'socketfile',         # socket file for unixsockets
                      'connection_type',    # tcp or local (unixsocket)
                      'blocking_timeout',   # whether socket is blocking (0.0 is non-blocking, positive floats are blocking timeouts, any negative value is ifinite timeout)
                      'nodelay',            # whether to turn off nagle
                      'rcvbuf',             # socket send buffer size
                      'sndbuf',             # socket recv buffer size
                      'rcvchunk',           # what chunksize to recv with
                      'sndchunk',           # what chunksize to send with
                      'fresh_socket',       # whether to reuse or generate a new socket
                      'verbose',            # whether to report during test
                      ]


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
    
    To minimize memory usage a base string of max size bytes is generated. This
    is used as base for other types as needed.
    """
    # We like predictable random for testing
    random.seed(42)
    numpy.random.seed(42)
    
    # find max size
    sizes = []
    for conf in confs:
        sizes.append( conf['msg_size'] )
    maxsize = max(sizes)
    base = ''.join([ chr(i%255) for i in xrange(maxsize) ])
    
    for conf in confs:
        size = conf['msg_size']
        if conf['msg_type'] == 'ascii':
            conf['data'] = base[0:size]
            
        elif conf['msg_type'] == 'numpy':
            dt = numpy.int64 # only this standard type for now
            conf['data'] = numpy.fromstring(base[0:size], dtype=dt)
            
        elif conf['msg_type'] == 'bytearray':
            try:
                conf['data'] = bytearray(base[0:size])
            except TypeError as e:        
                conf['data'] = bytearray(base[0:size].encode('latin-1')) # Python 3 needs special treatment
            
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
    nonblocking_safe_functions = [str_primitive_send_nb, str_buffer_send_nb, view_send_nb, numpy_send_nb]

    valid = True
    if conf['msg_size'] < 0:
        print("invalid conf msg_size:%s" % conf['msg_size'])
        valid = False

    if conf['blocking_timeout'] >= 0 and conf['send_function'] not in nonblocking_safe_functions:
        print("!!! %s is not listed as safe for non-blocking sockets - you'll have to VERIFY amount of data received every time" % (conf['send_function'].__name__) )
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
    connection.send(msg)

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
            #print( "ouch got:%s" % e )
            pass
        loopcount += 1
    if verbose:
        print("Sender looped %i times" % loopcount)

def str_buffer_send(connection,msg,verbose=False):
    """    
    Defunct in python 3 where buffer is replaced by memoryview
    """
    buf = buffer(msg)
    connection.send(buf)

def str_buffer_send_nb(connection,msg,verbose=False):
    """
    Robust enough for non-blocking sockets
    
    Defunct in python 3 where buffer is replaced by memoryview
    """
    loopcount = 0
    buf = buffer(msg)
    while buf:
        try:
            buf = buffer(buf, connection.send(buf))
        except socket.error as e:
            pass
        loopcount += 1
    if verbose:
        print("Sender looped %i times" % loopcount)


def view_send_nb(connection,msg,verbose=False):
    """
    Robust enough for non-blocking sockets
    
    Defunct in python 2.6 for lack of memoryview
    """
    loopcount = 0
    view = memoryview(msg)
    while view:
        try:
            view = view[connection.send(view):]
        except socket.error as e:
            pass
        loopcount += 1
    
    if verbose:
        print("Sender looped %i times" % loopcount)


def numpy_send(connection,msg,verbose=False):
    """
    sending numpy arrays with no pickling or bytearrays
    """
    npview = msg.view(numpy.uint8)
    connection.send(npview)

def numpy_send_nb(connection,msg,verbose=False):
    """
    Robust enough for non-blocking sockets
    """
    loopcount = 0
    npview = msg.view(numpy.uint8)
    length = len(npview)
    sent = 0
    while sent < length:
        try:
            sent += connection.send(npview)
        except socket.error as e:
            pass
        loopcount += 1

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
def sender(conf):
    def setup_connection(portno,address):
        maxtries = 3
        tries = 1
        while tries < maxtries:
            try:
                if conf['connection_type'] == "local":
                    if conf['verbose']:                    
                        print("Creating local socket to file %s" % (conf['socketfile']))
                    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client_socket.connect(conf['socketfile'])
            
                elif conf['connection_type'] == "tcp":
                    if conf['verbose']:
                        print("Creating TCP socket to (%s, %s)" % (portno,address))
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if conf['nodelay']:
                        client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
                    if 'sndbuf' in conf:
                        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,conf['sndbuf'])

                    bufs = client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
                    nodelay = client_socket.getsockopt(socket.SOL_TCP, socket.TCP_NODELAY)

                    client_socket.connect( (address, portno))
                     # set it to blocking AFTER connecting to avoid "[Errno 115] Operation now in progress"
                    if (not conf['blocking_timeout'] is None) and conf['blocking_timeout'] < 0.0:
                        client_socket.setblocking(1)
                    else:
                        client_socket.settimeout(conf['blocking_timeout'])
                    print("Connected TCP socket SO_SNDBUF:%i TCP_NODELAY:%i timeout:%s" % (bufs, nodelay, client_socket.gettimeout()) )
            except socket.error as e:
                print("got a socket error (%s) trying again..." % e)
                tries += 1
                time.sleep(tries) # give receiver time to open listening socket

            return client_socket
    
    msg = conf['data']
    iterations = conf['iterations']
    size = conf['msg_size']
    func = conf['send_function']
    
    connection = setup_connection(conf['port'],conf['host'])
    
    t1 = time.time()        
    for i in xrange(conf['iterations']):
        func(connection, msg, conf['verbose'])
    t2 = time.time()
    
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()
    
    print("(%i KB/s) -- %s -- sent %i times %i bytes(*) in %f seconds" % ((iterations*size)/(1024*(t2-t1)), func.__name__,iterations,size,t2-t1) ) 


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
            if conf['nodelay']:
                client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
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
        size = conf['msg_size']
        iterations = conf['iterations']
        msg_type = conf['msg_type']
        prebuf = conf.get('prebuf',False)
        
        # pregenerate a container if buffer-reuse is in effect
        if prebuf:
            container = generate_container(msg_type,size)
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
        

def sink(conf):
    def setup_connection(portno,address):
        if conf['connection_type'] == "local":
            socketfile = conf['socketfile']
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                server_socket.bind(socketfile)
            except socket.error as e:
                # if the file already exists remove it first
                os.remove(socketfile)
                server_socket.bind(socketfile)
                
            server_socket.listen(10)                
            print("Sink listening on file:%s" % (socketfile) )
    
        elif conf['connection_type'] == "tcp":            
            unbound = True
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if conf['nodelay']:
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
    
    server_socket = setup_connection(conf['port'],conf['host'])
    chunksize = conf['rcvchunk']
    try:
        while True:
            total = 0
            max_received = 0
            connection, address = server_socket.accept()
            #address = server_socket.accept()
            print("Sink (chunksize:%i) accepted connection from %s" % (chunksize ,address) )
            while True:
                try:
                    data = connection.recv(chunksize)
                    if data:
                        l = len(data)
                        total += l
                        if l == chunksize:
                            max_received += 1
                            #print( "got datalen:%s \t%s" % (l, "" if l < chunksize else "!") )
                    else:
                        print( "sink got empty data (connection closed) after receiving %i bytes" % total )
                        break
                except Exception as e:
                    print( "inner loop got exception:%s" % e )
                    break
                
            print("sink had %i receptions of max size, SO_RCVBUF:%i" % (max_received, server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)) )
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            
    except KeyboardInterrupt as e:
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
        print("sink stopped")
    

def runner():
    # Parse args
    parser = optparse.OptionParser()
    parser.add_option("-P", "--port", dest="port", default=15001, type=int,
                      help="which port to use")
    parser.add_option("-H", "--host", dest="host", default="127.0.0.1",
                      help="which host address to use")
    (options, args) = parser.parse_args()

    type = None
    if 's' in args or 'sender' in args:
        type = 'sender'
    elif 'r' in args or 'receiver' in args:
        type = 'receiver'
    else:
        type = 'sink'
    

    # generate base benchmark configuration
    baseconf = {
                'process_type' : type,
                'msg_size' : 10**3,
                'msg_type' : 'ascii',
                'iterations' : 3,
                'send_function' : str_primitive_send,
                'recv_function' : str_primitive_recv,
                'port' : options.port,
                'host' : options.host,
                'socketfile' : '/tmp/pupySockTest',
                'connection_type' : 'tcp',
                'blocking_timeout' : None,
                'nodelay' : True,
                'rcvchunk' : 4096,
                'fresh_socket' : False,
                'verbose' : True,
    }

    # generate individual benchmark configurations
    minimal_configurations = [baseconf]
    
    all_senders = []
    for f in (str_primitive_send, str_primitive_send_nb, str_buffer_send, str_buffer_send_nb):
        c = copy.copy(baseconf)
        c['send_function'] = f
        c['msg_size'] = 10**7
        c['iterations'] = 4
        all_senders.append(c)
    
    # this conf should generate non-blocking warning
    normal_conf = copy.copy(baseconf)
    normal_conf['msg_size'] = 10**7
    normal_conf['iterations'] = 4
    normal_conf['blocking_timeout'] = 0.0
    normal_configurations = [normal_conf]
    
    nb_senders = []
    for f in (str_primitive_send_nb, str_buffer_send_nb):
        c = copy.copy(baseconf)
        c['send_function'] = f
        c['msg_size'] = 10**7
        c['iterations'] = 4
        c['blocking_timeout'] = 0.0
        nb_senders.append(c)
    
    unixsock_conf = copy.copy(baseconf)
    unixsock_conf['send_function'] = str_primitive_send
    unixsock_conf['connection_type'] = 'local'
    us_configurations = [unixsock_conf]

    view_conf = copy.copy(baseconf)
    view_conf['msg_size'] = 10**6
    view_conf['msg_type'] = 'bytearray'
    view_conf['send_function'] = view_send_nb
    view_conf['iterations'] = 4
    view_conf['blocking_timeout'] = 0.0
    py27_configurations = [view_conf]

    numpy_conf = copy.copy(baseconf)
    numpy_conf['msg_size'] = 10**7
    numpy_conf['msg_type'] = 'numpy'
    numpy_conf['send_function'] = numpy_send_nb
    numpy_conf['iterations'] = 4
    numpy_conf['blocking_timeout'] = 0.0
    numpy_conf2 = copy.copy(numpy_conf)
    numpy_conf2['blocking_timeout'] = None
    numpy_conf2['send_function'] = numpy_send_nb
    numpy_configurations = [numpy_conf, numpy_conf2]

    # Switcheroo
    #configurations = minimal_configurations
    #configurations = normal_configurations
    #configurations = nb_senders
    #configurations = us_configurations
    #configurations = all_senders
    #configurations = py27_configurations
    configurations = numpy_configurations
    
    configurations = all_senders + nb_senders + numpy_configurations
    
    
    # Validate
    map(validate_conf,configurations)
    # data is not generated until now to minimize waste
    generate_data(configurations)
    
    sock = None
    # Execute configurations
    for conf in configurations:        
        if type=='sender':
            sender(conf)
        elif type=='receiver':
            receiver(conf)
        else:
            sink(conf)
            break # reuse same sink for many confs
        
    print("done running %i configurations" % (len(configurations)))
    
runner()
