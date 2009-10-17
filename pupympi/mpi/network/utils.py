import socket, struct
from mpi.logger import Logger
import random

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
def get_socket(min=10000, max=30000):
    """
    A simple helper method for creating a socket,
    binding it to a random free port within the specified range. 
    """
    logger = Logger()
    used = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    
    hostname = socket.gethostname()
    port_no = None

    #logger.debug("get_socket: Starting loop with hostname %s" % hostname)

    while True:
        port_no = random.randint(min, max) 
        if port_no in used:
            logger.debug("get_socket: Port %d is already in use %d" % port_no)
            continue

        try:
            #logger.debug("get_socket: Trying to bind on port %d" % port_no)
            sock.bind( (hostname, port_no) )
            break
        except socket.error, e:
            logger.debug("get_socket: Permission error on port %d" % port_no)
            used.append( port_no ) # Mark socket as used (or no good or whatever)
            raise e
        
    #logger.debug("get_socket: Bound socket on port %d" % port_no)
    return sock, hostname, port_no

def get_raw_message(client_socket):
    """
    The first part of a message is the actual size (N) of the message. The
    rest is N bytes of pickled data. So we start by receiving a long and
    when using that value to unpack the remaining part.
    
    NOTE: if we recieve to much we should pass on the remaining part
    """
    def receive_fixed(length):
        """Black box - Receive a fixed amount from a socket in batches not larger than 4096 bytes"""
        message = ""
        while length:
            data = client_socket.recv(min(length, 4096))
            length -= len(data)
            message += data
        return message
    
    header_size = struct.calcsize("ll")
    header = receive_fixed(header_size)
    message_size, rank = struct.unpack("ll", header)
    
    return rank, receive_fixed(message_size)
    
def prepare_message(data, rank):
    pickled_data = pickle.dumps(data)
    header = struct.pack("ll", len(pickled_data), rank)
    return header+pickled_data