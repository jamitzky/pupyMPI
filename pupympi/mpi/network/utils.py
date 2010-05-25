#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
import socket, struct
import random

from mpi.logger import Logger
from mpi.exceptions import MPIException

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
def create_random_socket(min=10000, max=30000):
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
        except socket.error:
            logger.debug("get_socket: Permission error on port %d, trying a new one" % port_no)
            used.append( port_no ) # Mark socket as used (or no good or whatever)
            continue
        
    return sock, hostname, port_no

def get_raw_message(client_socket):
    """
    The first part of a message is the actual size (N) of the message. The
    rest is N bytes of pickled data. So we start by receiving a long and
    when using that value to unpack the remaining part.
    """
    def receive_fixed(length, header=False):
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
                #raise Exception
                raise MPIException("Connection broke or something received empty (still missing length:%i - header:%s)" %(length,header))
                

            length -= len(data)
            message += data
                
        return message
    
    header_size = struct.calcsize("lll")
    header = receive_fixed(header_size,False)
    message_size, rank, cmd = struct.unpack("lll", header)
    
    return rank, cmd, receive_fixed(message_size,True)
    
def prepare_message(data, rank, cmd=0):
    # DEBUG
    if data[2] == 44:
        #data = (data[0],data[1],data[2],data[3],data[4][0:-1])2
        #data = (data[0],data[1],7,data[3],data[4]) # WIN
        #data = (data[0],data[1],111,data[3],data[4]) # WIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"wwww") # WINWIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"www") # FAIL
        #data = (data[0],data[1],data[2],data[3],data[4]+"ww") # WIN
        #data = (data[0],data[1],data[2],data[3],data[4]+"w") # WIN
        pass

    
    
    pickled_data = pickle.dumps(data)
    lpd = len(pickled_data)
    #Logger().debug("Prepared message with command: %d, DATA:%s and lpd:%i" % (cmd,data,lpd) )
    # DEBUG
    # This actually allows the message to be sent, receiver fails since last byte promised is never sent
    #if data[2] == 44:
    #    lpd += 1        
    #if lpd % 2 != 0:
    #    lpd +=  1

    header = struct.pack("lll",lpd , rank, cmd)
    Logger().debug("Prepared message with command: %d, DATA:%s,len:%i, h+p:%i" % (cmd,data,lpd,len(header+pickled_data)) )
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
    except Exception:
        # This is an equally hackish way of removing nasty printing chars
        # a nicer way would be to use str.translate with appropriate mappings
        sdata = str(data)
        # _ is hexysymbols
        _, sep, rest = sdata.partition("(I")
        # Now tcp control chars garble garble has been removed
        data = (sep+rest).replace("\n","<n>")
        return data

def robust_send(socket, message):
    """
    Python docs state that using socket.send the application is responsible for
    handling any unsent bytes. Even though we have not really seen it yet we use
    this wrapper to ensure that it all really gets sent.
    """
    target = len(message) # how many bytes to send
    transmitted_bytes = 0
    Logger().debug("... robust_send target:%i, message:%s" %(target,message))
    while target > transmitted_bytes:        
        delta = socket.send(message)
        transmitted_bytes += delta
        Logger().debug("... target")
        if target > transmitted_bytes: # Rare unseen case therefore relegated to if clause instead of always slicing in send
            message = message[transmitted_bytes:]
            Logger().debug("Message sliced because it was too large for one send.")
        
