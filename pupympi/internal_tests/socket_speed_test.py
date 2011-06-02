import threading
import os
import time
import tempfile
import socket
import random
import string
#import twiggy
import sys
import numpy

"""
This module is for benchmarking different methods of sending data over Python
sockets.

A message is sent repeatedly from sender to receiver. The receiver validates that
no corruption of the data ocurred en route.
The costs of setting up and tearing down the connection are not counted, as this
should be the same for all methods. The cost of validating the correctness is
not counted either since this is just for ensuring correctness during development.

NOTES:
- Testing does not show the expected results so far. Possible variations:
  - limit receiver to smaller chunks
  - check TCP protocol weirdness via Wireshark
  - Try limiting sender via TCP options
  - Try with TCP NODELAY (nagle off)

- For now we test with a message size known to both sides. This is intentional
  since we want to measure only the simplest recv and send loops. In the
  practical applications we need to have the header received examined before
  receiving the payload but this makes measuring more complicated and also
  depends on eg. the header format chosen. So we postpone this.
  
ISSUES:
- When running multiple functions under one conf, prebuf can conflict with validation and type may conflict too
- Pregenerated data should only be generated once for each requested type, and of maximum size (confs needing less can slice)
- Turn off delayed ack/nagle for connections
- Validation of conf should include python version
- Occasionally the port is not freed before attempting next connection setup, maybe sleep between, or increment port number for each conf
"""


### AUXILLARY

def clear_port(portno):
    """
    return first available port from portno and up

    make sure that the chosen port is available by binding it succesfully and
    then closing it
    """
    unbound = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while unbound:
        try:
            server_socket.bind( ('127.0.0.1', portno))
        except socket.error as e:    
            #raise e
            portno += 1
            print("port not available (error:%s), trying %i ..." % (e,portno) )           
        except Exception as e:
            print("unexpected error:%s" % e )
            raise e
        
        # success
        unbound = False
    
    server_socket.close()
    
    return portno


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
        if conf['msgtype'] == 'ascii':
            size = conf['msgsize']
            # only lowercase chars from alphabet
            conf['data'] = ''.join(random.choice(string.ascii_lowercase) for i in range(size))
            
        elif conf['msgtype'] == 'numpy':
            size = conf['msgsize'] // 8 # int64 array is 8 bytes per element
            #conf['data'] = numpy.array(range(size)) # linear
            conf['data'] = numpy.random.random_integers(0,size,size )  # numpy random
            
        elif conf['msgtype'] == 'bytearray':
            size = conf['msgsize']
            #bytestring = ''.join([ 'a' for i in range(size) ])
             # TODO: make more random
            bytestring = ''.join([ chr(i%255) for i in range(size) ])
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

def str_primitive_send(connection,msg):
    size = len(msg)
    sent = 0
    while sent < size:
        sent += connection.send(msg[sent:])
        
def str_buffer_send(connection,msg):
    """
    This seems suboptimal. It looses to str_primitive_send on both 2.6 and 2.7
    when testing via localhost.
    
    Defunct in python 3 where buffer is replaced by memoryview
    """
    buf = buffer(msg)
    while len(buf):
        buf = buffer(msg,len(buf) + connection.send(buf))

def str_view_send(connection,msg):
    """
    Works for both 2.7 and 3.1
    """
    bytesize = len(msg)
    sent = 0
    view = memoryview(msg.encode('latin1'))
    while sent < bytesize:        
        sent += connection.send(view[sent:])


def numpy_send(connection,msg):
    """
    for now this is the same as primitive send, but we should determine whether
    time is saved by using a view over the numpy array in the loop instead of normal slice
    """
    bytesize = msg.nbytes
    sent = 0
    while sent < bytesize:
        sent += connection.send(msg[sent:])
    # DEBUG
    #print("sent a numpy array of %i type:%s element-type:%s" % (len(msg),type(msg),type(msg[0])))

        
def bytearray_send(connection,msg):
    bytesize = len(msg) # len equals size for bytearrays
    sent = 0
    view = memoryview(msg)
    while sent < bytesize:
        sent += connection.send(view[sent:])


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
def sender(dummy,confs):
    def setup_connection(portno,address):
        maxtries = 3
        tries = 1
        while tries < maxtries:
            time.sleep(tries) # give receiver time to open listening socket
            print("Sender trying port:%i try:%i" % (portno,tries))
            try:
                if conf['connection_type'] == "local":
                    #Logger().debug("Creating local socket to %s" % connection_info)
                    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    client_socket.connect(socketfile)
                    return client_socket
            
                elif conf['connection_type'] == "tcp":
                    #Logger().debug("Creating TCP socket to (%s, %s)" % connection_info)
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)            
                    client.connect( (address, portno))
                    return connection
            except socket.error:
                tries += 1
    
    # Run configurations that are to be tested
    for conf in confs:
        if not validate_conf(conf):
            continue
        
        functions = conf['sfunctions']
        msg = conf['data']
        iterations = conf['iterations']
        size = conf['msgsize']
        
        for func in functions:
            connection = setup_connection(conf['port'],conf['address'])
            ## DEBUG
            #print("Sender sending %s" % msg)
            
            t1 = time.time()        
            for i in range(conf['iterations']):
                func(connection, msg)
            t2 = time.time()
            
            connection.close()
            
            print("(%i kB/s) -- %s -- sent %i times %i bytes(*) in %f seconds" % ((iterations*size)/(1024*(t2-t1)), func.__name__,iterations,size,t2-t1) ) 


def receiver(dummy,confs,validate=True):
    def setup_connection(portno,address):
        print("Receiver starting with port no:%i" % portno)
        if conf['connection_type'] == "local":
            global socketfile
            socketfile = tempfile.NamedTemporaryFile()
            #Logger().debug("Creating local socket to %s" % connection_info)
            server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_socket.bind(socketfile)
    
        elif conf['connection_type'] == "tcp":
            #Logger().debug("Creating TCP socket to (%s, %s)" % connection_info)
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        
            server_socket.bind((address, portno))
            server_socket.listen(10)
            
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
                for i in range(iterations):                
                    # DEBUG
                    #print("C1: %s" % container)
                    func(connection, size, container)
                t2 = time.time()
            else:
                if validate: # if not reusing buffer, validation requires storing all transmitted data
                    received_data = []
                    
                    t1 = time.time()
                    for i in range(iterations):
                        received_data.append( func(connection, size, container) )
                    t2 = time.time()
                else:
                    t1 = time.time()
                    for i in range(iterations):
                        # DEBUG
                        #print("C1: %s" % container)
                        container = func(connection, size, container)                    
                    t2 = time.time()
    
            # DEBUG
            #print("C2: %s" % container)
            
            connection.close()
            
            if validate:
                if prebuf:
                    received_data = [container]
                validate_results(received_data,conf['data'])
                
            print("(%i kB/s) -- %s -- got %i times %i bytes(*) in %f seconds" % ((iterations*size)/(1024*(t2-t1)), func.__name__,iterations,size,t2-t1))
        

    
def runner():
    localhost = '127.0.0.1' # Feels like localhost
    startport = 15001    
    testport = clear_port(startport)
    
    # Python 2.6 compatible
    testconf1 = {
        "iterations" : 10000,
        "msgsize" : 800, # always in bytes
        "msgtype" : 'ascii',
        #"sfunctions" : [str_primitive_send, str_buffer_send],
        #"rfunctions" : [str_primitive_recv, str_list_recv],
        #"sfunctions" : [str_primitive_send, str_buffer_send,str_primitive_send, str_buffer_send],
        #"rfunctions" : [str_primitive_recv, str_primitive_recv, str_list_recv, str_list_recv],
        "sfunctions" : [str_primitive_send, str_primitive_send, str_buffer_send, str_buffer_send],
        "rfunctions" : [str_primitive_recv, str_list_recv,str_primitive_recv, str_list_recv],
        #"sfunctions" : [str_buffer_send,str_primitive_send],
        #"rfunctions" : [str_list_recv,str_primitive_recv],
        "port" : testport,  # This one should be pre-cleared
        "address" : localhost,
        "connection_type" : 'tcp',
    }

    testconf2 = {
        "iterations" : 10000,
        "msgsize" : 4000, # always in bytes
        "msgtype" : 'ascii',
        "sfunctions" : [str_buffer_send],
        "rfunctions" : [str_list_recv],
        "port" : testport,  # This one should be pre-cleared
        "address" : localhost,
    }
    
    # Python 2.7 and up
    testconf3 = {
        "iterations" : 10000,
        "msgsize" : 4000, # always in bytes
        "msgtype" : 'numpy',
        "sfunctions" : [numpy_send],
        "rfunctions" : [numpy_recv],
        "port" : testport,  # This one should be pre-cleared
        "address" : localhost,
        "prebuf" : True,
    }
    
    # Python 2.7 and up
    testconf4 = {
        "iterations" : 1000000,
        "msgsize" : 4000, # always in bytes
        "msgtype" : 'bytearray',
        "sfunctions" : [bytearray_send],
        "rfunctions" : [bytearray_recv],
        "port" : testport,  # This one should be pre-cleared
        "address" : localhost,
        "prebuf" : True,
    }
    
    # Python 2.7 and up
    testconf5 = {
        "iterations" : 10000,
        "msgsize" : 4000, # always in bytes
        "msgtype" : 'ascii',
        "sfunctions" : [str_view_send],
        #"rfunctions" : [str_list_recv],
        "rfunctions" : [str_decoding_recv],
        "port" : testport,  # This one should be pre-cleared
        "address" : localhost,
    }

    # Switcheroo
    configurations = [testconf1]
    #configurations = [testconf2]
    #configurations = [testconf3]
    #configurations = [testconf4]
    #configurations = [testconf5]
    
    #configurations = [testconf1,testconf2,testconf3,testconf4,testconf5]
    #configurations = [testconf1,testconf2,testconf3,testconf4]
    #configurations.reverse()
    
    #validate = True
    validate = False
        
    generate_data(configurations) # pre-generate data to ensure that both ends have same set
    
    t1 = threading.Thread(target=receiver, args=("dummmy",configurations,validate), kwargs={})
    t2 = threading.Thread(target=sender, args=("dummmy",configurations), kwargs={})
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("done running %i configurations with validation %s" % (len(configurations), "ON" if validate else "OFF"))
    
runner()