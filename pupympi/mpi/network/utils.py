import socket, struct
import random

from mpi.logger import Logger
from mpi.exceptions import MPIException

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
            logger.debug("get_socket: We know port %d is already in use, try a new one" % port_no)
            continue

        try:
            #logger.debug("get_socket: Trying to bind on port %d" % port_no)
            sock.bind( (hostname, port_no) )
            break
        except socket.error, e:
            logger.debug("get_socket: Permission error on port %d, trying a new one" % port_no)
            used.append( port_no ) # Mark socket as used (or no good or whatever)
            continue
            # NOTE: I am quite sure we should not raise further here or at least not in the normal
            # exception case where we happen to hit a used socket. Instead we go on
            # and that actually means we can potentially use the used-list for something.
            #raise e
        
    #logger.debug("get_socket: Bound socket on port %d" % port_no)
    return sock, hostname, port_no

def get_raw_message(client_socket, shutdown=False):
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
        bad_recieves = 0
        #if shutdown:            
        #    Logger().debug("... length was: %s -  and shutdown is in progress!!!" % length)
            #if self.shutdown_event.is_set():
            #    Logger().debug("... FEDT")
        # FIXME: Try lowering to only one bad recieve and see if it isn't just normal
        # operation for a closed socket
        while length and bad_recieves < 10:
            try:
                #client_socket.settimeout(3.0)
                data = client_socket.recv(min(length, 4096))
                # DEBUG
                #if shutdown:
                #    Logger().debug("... recv gave something -  and shutdown is in progress!!!")
            except socket.error, e:
                Logger().debug("recieve_fixed: recv() threw:%s for socket:%s length:%s message:%s" % (e,client_socket, length,message))
                raise MPIException("Connection broke or something")
                # NOTE: We can maybe recover more gracefully here but that requires
                # throwing status besides message and rank upwards. For now I just want
                # to be aware of this error when it happens.
            except Exception, e:
                Logger().error("get_raw_message: Raised error: %s" %e)
                raise MPIException("Connection broke or something")
            length -= len(data)
            message += data
            if message == "":
                bad_recieves += 1
                
        if message == "":
            raise MPIException("Connection broke or something - bad_recieves: %i" % bad_recieves)
        else:
            return message
    
    header_size = struct.calcsize("lll")
    if shutdown:
        Logger().debug("... trying to recieve fixed -  and shutdown is in progress!!!")
    header = receive_fixed(header_size)
    if shutdown:
        Logger().debug("... recieved fixed -  and shutdown is in progress!!!")
    message_size, rank, cmd = struct.unpack("lll", header)
    
    return rank, cmd, receive_fixed(message_size)
    
def prepare_message(data, rank, cmd=0):
    Logger().debug("Preparing message with command: %d" % cmd)
    pickled_data = pickle.dumps(data)
    header = struct.pack("lll", len(pickled_data), rank, cmd)
    return header+pickled_data

def _nice_data(data):
    """
    Internal function to allow safer printing/logging of raw data
    Tries to eliminate the hex (?) ASCII symbols that appear as tcp-like
    control packets.
    
    NOTE: If we one day find something useful to do based on the control codes,
    we should convert them nicely to string instead, but for now this will do.
    
    There are some nice functions here to accomplish conversion of the byte-strings
    http://docs.python.org/c-api/string.html#string-bytes-objects
    """
    if data == None:
        return None
    
    # This is a hackish way of detecting if data is pickled or not
    # We try to unpickle and if it fails it is probably not pickled
    try:
        unpickled = pickle.loads(data)
        return unpickled
    except Exception, e:
        # This is an equally hackish way of removing nasty printing chars
        # a nicer way would be to use str.translate with appropriate mappings
        sdata = str(data)
        hexysymbols, sep, rest = sdata.partition("(I")
        # Now tcp control chars garble garble has been removed
        data = (sep+rest).replace("\n","<n>")
        
        return data

def robust_send(socket, message):
    """
    Python docs state that using socket.send the application is responsible for
    handling any unsent bytes. Even though we have not really seen it yet we use
    this wrapper to ensure that it all really gets sent.
    """
    # FIXME: Decide whether to catch errors here and reraise or as now let caller handle
    
    remainder = len(message) # how many bytes to send
    while remainder > 0:
        transmitted_bytes = socket.send(message)
        remainder -= transmitted_bytes
        
