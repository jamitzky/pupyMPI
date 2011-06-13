#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
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
import socket, struct, random, numpy

from mpi.logger import Logger
from mpi.exceptions import MPIException
from mpi import constants
from mpi.commons import pickle

HEADER_FORMAT = "lllllll"

def create_random_socket(min=10000, max=30000):
    """
    A simple helper method for creating a socket,
    binding it to a random free port within the specified range.
    """
    logger = Logger()
    used = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Enable TCP_NODELAY to improve performance of sending one-off packets by
    # immediately acknowledging received packages instead of trying to
    # piggyback the ACK on the next outgoing packet (Nagle's algorithm)
    # XXX: If you remove this, remember to do so in socketpool as well.
    sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    #sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    hostname = socket.gethostname()
    port_no = None

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

def get_raw_message(client_socket, bytecount=4096):
    """
    The first part of a message is the actual size (N) of the message. The
    rest is N bytes of pickled data. So we start by receiving a long and
    when using that value to unpack the remaining part.
    """
    def receive_fixed(length):
        """
        Black box - Receive a fixed amount from a socket in batches not larger than 4096 bytes
        """
        #Logger().debug("recieve_fixed: length:%s" % (length))
        message = ""
        while length > 0:
            try:
                data = client_socket.recv(min(length, bytecount))
            except socket.error, e:
                #Logger().debug("recieve_fixed: recv() threw:%s for socket:%s length:%s message:%s" % (e,client_socket, length,message))
                raise MPIException("recieve_fixed threw socket error: %s" % e)
                # NOTE: We can maybe recover more gracefully here but that requires
                # throwing status besides message and rank upwards.
            except Exception, e:
                #Logger().error("get_raw_message: Raised error: %s" %e)
                raise MPIException("recieve_fixed threw other error: %s" % e)

            # Other side closed
            if len(data) == 0:
                raise MPIException("Connection broke or something received empty (still missing length:%i)" % length)

            length -= len(data)
            message += data

        return message

    header_size = struct.calcsize(HEADER_FORMAT)
    header = receive_fixed(header_size)
    lpd, rank, cmd, tag, ack, comm_id, coll_class_id = struct.unpack(HEADER_FORMAT, header)
    # DEBUG
    #Logger().debug("recieved: length:%s tuple:%s" % (header_size, (lpd, rank, cmd, tag, ack, comm_id )))
    return rank, cmd, tag, ack, comm_id, coll_class_id, receive_fixed(lpd)


# ... just for later inspiration
othertypes = {
    # The bytearray type will have to be handled differently since an element has int type etc.
    constants.CMD_BYTEARRAY : {"type" : bytearray, "bytesize" : 1, "description" : "raw bytearray" },
}

numpytypes = {
    constants.CMD_RAWTYPE+101 : {"type" : numpy.dtype('bool'), "bytesize" : 1, "description" : "Boolean (True or False) stored as a byte"},
    constants.CMD_RAWTYPE+102 : {"type" : numpy.dtype('int8'), "bytesize" : 1, "description" : "Byte (-128 to 127)" },
    constants.CMD_RAWTYPE+103 : {"type" : numpy.dtype('int16'), "bytesize" : 2, "description" : "Integer (-32768 to 32767)" },
    constants.CMD_RAWTYPE+104 : {"type" : numpy.dtype('int32'), "bytesize" : 4, "description" : "Integer (-2147483648 to 2147483647)" },
    constants.CMD_RAWTYPE+105 : {"type" : numpy.dtype('int64'), "bytesize" : 8, "description" : "Integer (9223372036854775808 to 9223372036854775807)" },
    constants.CMD_RAWTYPE+106 : {"type" : numpy.dtype('uint8'), "bytesize" : 1, "description" : "Unsigned integer (0 to 255)" },
    constants.CMD_RAWTYPE+107 : {"type" : numpy.dtype('uint16'), "bytesize" : 2, "description" : "Unsigned integer (0 to 65535)" },
    constants.CMD_RAWTYPE+108 : {"type" : numpy.dtype('uint32'), "bytesize" : 4, "description" : "Unsigned integer (0 to 4294967295)" },
    constants.CMD_RAWTYPE+109 : {"type" : numpy.dtype('uint64'), "bytesize" : 8, "description" : "Unsigned integer (0 to 18446744073709551615)" },
    constants.CMD_RAWTYPE+110 : {"type" : numpy.dtype('float32'), "bytesize" : 4, "description" : "Single precision float: sign bit, 8 bits exponent, 23 bits mantissa" },
    constants.CMD_RAWTYPE+111 : {"type" : numpy.dtype('float64'), "bytesize" : 8, "description" : "Double precision float: sign bit, 11 bits exponent, 52 bits mantissa" },
    constants.CMD_RAWTYPE+112 : {"type" : numpy.dtype('complex64'), "bytesize" : 8, "description" : "Complex number, represented by two 32-bit floats (real and imaginary components)" },
    constants.CMD_RAWTYPE+113 : {"type" : numpy.dtype('complex128'), "bytesize" : 16, "description" : "Complex number, represented by two 64-bit floats (real and imaginary components)" },
}

# Mapping dicts
#typeint_to_numpytype = dict( [(typeint,desc['type']) for typeint,desc in numpytypes.items() ] )
#numpytype_to_typeint = dict( [(desc['type'],typeint) for typeint,desc in numpytypes.items() ] )

typeint_to_type = dict( [(typeint,desc['type']) for typeint,desc in numpytypes.items()+othertypes.items() ] )
type_to_typeint = dict( [(desc['type'],typeint) for typeint,desc in numpytypes.items()+othertypes.items() ] )
def prepare_multiheader(rank, cmd=0, tag=constants.MPI_TAG_ANY, ack=False, comm_id=0, payload_length=0, collective_header_information=()):
    """
    Internal function to
    - construct header for a list of already serialized payloads
    
    NOTE: Caller is assumed to know the combined length of the payloads since
          initial serialization and the segmentation has been done by the caller
    
    The header format is the traditional
    """      
    try:
        coll_class_id = collective_header_information[0]
    except IndexError, e:
        coll_class_id = -1

    header = struct.pack(HEADER_FORMAT, payload_length, rank, cmd, tag, ack, comm_id, coll_class_id)
    return header

def get_shape(shapebytes):
    return tuple(numpy.fromstring(shapebytes,numpy.dtype(int)))

def prepare_message(data, rank, cmd=0, tag=constants.MPI_TAG_ANY, ack=False, comm_id=0, is_serialized=False, collective_header_information=()):
    """
    Internal function to
    - serialize payload if needed
    - measure payload
    - construct header
    
    The header format has following fields:
    length of payload
    rank of sender
    system cmd
    mpi or system tag
    acknowledge needed
    communicator id
    
    TODO: We might not have to create a header always. In at least one place we chop off header to reuse, this is wasteful
    """
    if is_serialized:
        # DEBUG
        try:
            Logger().debug("using already pickled data! type:%s data:%s" % (type(data), pickle.loads(data)) )
        except:
            Logger().debug("using already serialized data! type:%s data:%s" % (type(data), data) )
        serialized_data = data
    else:
        serialized_data, cmd = serialize_message(data,cmd)
       
    header =  prepare_multiheader(rank, cmd=cmd, tag=tag, ack=ack, comm_id=comm_id, payload_length=len(serialized_data), collective_header_information=collective_header_information)
    return (header,serialized_data)

def serialize_message(data, cmd=None, recipients=1):
    """
    Internal function to
    - measure and serialize payload
    - construct proper msg_type (cmd) including possible shapebytes
    
    NOTE:
    The recipients parameter only takes effect when scattering multi-dimensional
    numpy arrays. Here shapebytes are adjusted to reflect the final (scattered)
    shape
    """
    if isinstance(data,numpy.ndarray):
        # Multidimensional array?
        if len(data.shape) > 1:
            # DEBUG
            #Logger().debug("prepare MULTI - type:%s " % (data.dtype) )

            # Transform the shape to a bytearray (via numpy array since shape might contain ints larger than 255)
            if recipients > 1:
                # If the array is to be scattered, the first dimension is proportionally smaller
                shape_array = numpy.array(data.shape)
                shape_array[0] = shape_array[0] / recipients
                byteshape = shape_array.tostring()
            else:
                byteshape = numpy.array(data.shape).tostring()
            # Note how many bytes are shape bytes
            shapelen = len(byteshape)
            # Look up the correct type int
            cmd = type_to_typeint[data.dtype]
            # Store shapelen in the upper decimals of the cmd
            cmd = shapelen*1000 + cmd
            # FIXME: This is another unneccessary string allocation.
            #        We need to keep payload separated into shapebytes and the bytes making up the actual numpy array
            # Convert data to bytearray with shape prepended
            serialized_data = byteshape + data.tostring()
            
            # DEBUG
            Logger().debug("prepare MULTI - type:%s shape:%s" % (data.dtype, data.shape) )

            # BELOW WORKS WITH NUMPY >= 1.5                
            ## Transform the shape to a bytearray (via numpy array since shape might contain ints larger than 255)
            #byteshape = bytearray(numpy.array(data.shape))
            ## Note how many bytes are shape bytes
            #shapelen = len(byteshape)                
            ## Look up the correct type int
            #cmd = numpytype_to_typeint[data.dtype]
            ## Store shapelen in the upper decimals of the cmd
            #cmd = shapelen*1000 + cmd
            ## Convert data to bytearray with shape prepended
            #serialized_data = byteshape + bytearray(data)            
        else:
            
            serialized_data = data.tostring()
            
            # BELOW WORKS WITH NUMPY >= 1.5                
            #serialized_data = bytearray(data)
            
            # Look up the correct type int
            cmd = type_to_typeint[data.dtype]
            Logger().debug("prepare ONEDIM - type:%s cmd:%s" % (type(data[0]), cmd) )
    elif isinstance(data,bytearray):            
        cmd = type_to_typeint[type(data)]
        Logger().debug("prepare BYTEARRAY - cmd:%i len:%s" % (cmd,len(data)) )
        serialized_data = data
    else:
        # NOTE: cmd is not overwritten for vanilla pickling since it is up to caller to decide between eg. system message or user message
        #Logger().debug("prepare VANILLA type:%s header:%s data:%s" %  (type(data),  (rank, cmd, tag, ack, comm_id), data) )
        serialized_data = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        
    return (serialized_data, cmd)

def deserialize_message(raw_data, msg_type):
    """
    Retrieve the original message from a payload given the message type
    """
    #Logger().debug("DESERIALIZING msgtype:%s" % msg_type)
    
    # Non-pickled data is recognized via msg_type
    if msg_type > constants.CMD_RAWTYPE:
        # Multidimensional arrays have the number of shapebytes hiding in the upper decimals
        shapelen = msg_type / 1000
        # typeint occupies the lower decimals
        typeint = msg_type % 1000
        if shapelen:
            # Slice shapebytes out of msg
            shapebytes = raw_data[:shapelen]
            # Restore shape tuple
            shape = tuple(numpy.fromstring(shapebytes,numpy.dtype(int)))
            # Lookup the numpy type
            t = typeint_to_type[typeint]
            # Restore numpy array from the rest of the string
            data = numpy.fromstring(raw_data[shapelen:],t).reshape(shape)
        
        else:
            # Numpy type or bytearray
            if msg_type == constants.CMD_BYTEARRAY:
                # plain old bytearray
                data = bytearray(raw_data)
            else:
                # Lookup the numpy type
                t = typeint_to_type[msg_type]
                # Restore numpy array
                # DEBUG try
                try:
                    data = numpy.fromstring(raw_data,t)
                except Exception as e:
                    Logger().error("BAD FROMSTRING msg_type:%s len(raw_data):%i t:%s" % (msg_type,len(raw_data), t) )
                    raise e
                #data = numpy.fromstring(raw_data,t)
    else:
        try:
            # Both system messages and user pickled messages are unpickled here
            data = pickle.loads(raw_data)
        except Exception as e:
            Logger().error("BAD PICKLE msg_type:%s raw_data:%s" % (msg_type,raw_data) )
            raise e
    
    return data
        
def robust_send_multi(socket, messages):
    """
    experimental cousin of robust_send
    if we can agree that the overhead of always considering messages a list is negligible this can be folded into regular robust_send
    
    TODO: Check (eg. with wireshark) if every send produces a tcp packet or if several messages can be packed into on tcp packet (which we hope is what happens)
    """
    for message in messages:
        target = len(message) # how many bytes to send
        transmitted_bytes = 0
    
        while target > transmitted_bytes:
            delta = socket.send(message)
            transmitted_bytes += delta
    
            if target > transmitted_bytes: # Rare unseen case therefore relegated to if clause instead of always slicing in send
                message = message[transmitted_bytes:]
                Logger().debug("Message sliced because it was too large for one send.")

def robust_send(socket, message):
    """
    Python docs state that using socket.send the application is responsible for
    handling any unsent bytes. Even though we have not really seen it yet we use
    this wrapper to ensure that it all really gets sent.
    """
    target = len(message) # how many bytes to send
    transmitted_bytes = 0

    while target > transmitted_bytes:
        delta = socket.send(message)
        transmitted_bytes += delta

        if target > transmitted_bytes: # Rare unseen case therefore relegated to if clause instead of always slicing in send
            message = message[transmitted_bytes:]
            Logger().debug("Message sliced because it was too large for one send.")

