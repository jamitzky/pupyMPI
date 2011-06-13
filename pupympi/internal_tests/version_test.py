import sys
import random
import time
import timeit
import socket

import ctypes
import array

import struct
try:
    import cPickle as pickle
except ImportError:
    import pickle
    
def robust_send(socket, message):
    """
    Python docs state that using socket.send the application is responsible for
    handling any unsent bytes. Even though we have not really seen it yet we use
    this wrapper to ensure that it all really gets sent.
    """
    target = len(message) # how many bytes to send
    transmitted_bytes = 0
    print "... robust_send target:%i, message:%s" %(target,message)
    while target > transmitted_bytes:        
        delta = socket.send(message)
        transmitted_bytes += delta
        if target > transmitted_bytes: # Rare unseen case therefore relegated to if clause instead of always slicing in send
            message = message[transmitted_bytes:]
            print "Message sliced because it was too large for one send."

def get_raw_message(client_socket):
    """
    The first part of a message is the actual size (N) of the message. The
    rest is N bytes of pickled data. So we start by receiving a long and
    when using that value to unpack the remaining part.
    """
    def receive_fixed(length):
        """
        Black box - Receive a fixed amount from a socket in batches not larger than 4096 bytes
        """
        message = ""
        while length > 0:
            try:
                data = client_socket.recv(min(length, 4096))
            except socket.error, e:
                Logger().debug("recieve_fixed: recv() threw:%s for socket:%s length:%s message:%s" % (e,client_socket, length,message))
                raise MPIException("recieve_fixed threw socket error: %s" % e)
                # NOTE: We can maybe recover more gracefully here but that requires
                # throwing status besides message and rank upwards.
            except Exception, e:
                Logger().error("get_raw_message: Raised error: %s" %e)
                raise MPIException("recieve_fixed threw other error: %s" % e)
            
            # Other side closed
            if len(data) == 0:
                raise MPIException("Connection broke or something recieved empty")

            length -= len(data)
            message += data
                
        return message
    
    header_size = struct.calcsize("lll")
    header = receive_fixed(header_size)
    message_size, rank, cmd = struct.unpack("lll", header)
    
    return rank, cmd, receive_fixed(message_size)

def prepare_message(data, rank, cmd=0):
    # DEBUG
    if data[2] == 44:
        #data = (data[0],data[1],data[2],data[3],data[4][0:-1])2
        #data = (data[0],data[1],11,data[3],data[4]) # WIN
        #data = (data[0],data[1],111,data[3],data[4]) # WIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"wwww") # WINWIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"www") # FAIL
        #data = (data[0],data[1],data[2],data[3],data[4]+"ww") # WIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"w") # WIN
        pass

    
    pickled_data = pickle.dumps(data)
    lpd = len(pickled_data)
    #if data[2] == 44:
    #    lpd +=  1
    #if lpd % 2 != 0:
    #    lpd +=  1
    
    header = struct.pack("lll",lpd , rank, cmd)
    print "Prepared message with command: %d, DATA:%s,len:%i, h+p:%i" % (cmd,data,lpd,len(header+pickled_data))
    return header+pickled_data



def prp_receiver(address,port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, port))
    s.listen(1)
    print "string server setup"    
    conn, _ = s.accept()
    print "string server connected"

    more = True

    while more:
        try:
            rank, msg_command, _, _, _, raw_data = get_raw_message(conn)
        except Exception, e:
            print "some error...", str(e)
        
        print "Rank:%s,cmd:%s,raw_data:%s" % (rank,msg_command,raw_data)
        more = False
    
    conn.close()
    
def prp_sender(address,port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((address,port))
    print "string sender connected"
    
    tag = 44
    
    message = "This message was sent"

    data = (0, 0, tag, False, message)
    header,payload = prepare_message(data, 0, 0)    

    robust_send(s,header+payload)
    
    print "sender done"
    s.close()    
    

    
    
### STARTER

def starter():
    port = 2525
    address = "localhost"
    server = False

    sleeptime = 3

    for arg in sys.argv:
        if arg == "server":
            server = True
        elif arg.find("port:") > -1:
            token,sep,port = arg.partition(':')

    if server:
        prp_receiver(address,port)
    else:
        prp_sender(address,port)
        
    print "done"
        


starter()