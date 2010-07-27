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
import socket
import threading
from mpi.logger import Logger
from mpi.exceptions import MPIException

class SocketPool(object):
    """
    This class manages a pool of socket connections. You request and delete
    connections through this class.
    
    The class has room for a number of cached socket connections, so if your
    connection is heavily used it will probably not be removed. This way your
    call will not create and teardown the connection all the time. 
    
    NOTE: The number of cached elements are controlled through the constants 
    module, even though it might be exposed at a later point through command
    line arguments for mpirun.py
    
    NOTE 2: It's possible to mark a connections as mandatory persistent. This
    will not always give you nice performance. Please don't use this feature
    too much as it will push other connections out of the cache. And these
    connections might be more important than your custom one.
    
    IMPLEMENTATION: This is a modified "Second change FIFO cache replacement
    policy" algorithm. It's modified by allowing some elements to live 
    forever in the cache.
    And also an element given a second chance is not moved to the back of the "queue".
    
    ERRORS: It's possible to trigger an error if you fill up the cache with
    more persistent connections than the buffer can actually contain. An
    MPIException will be raised in this situation. 
    """
    
    def __init__(self, max_size):
        self.sockets = []
        self.max_size = max_size
        self.readonly = False #This will be set True during network initialization if a static socket pool is specified
        self.metainfo = {}
        
        self.sockets_lock = threading.Lock()
        
    def get_socket(self, rank, socket_host, socket_port, force_persistent=False):
        """
        Returns a socket to the specific rank. Consider this function 
        a black box that will cache your connections when it is 
        possible.
        """
        client_socket = self._get_socket_for_rank(rank) # Try to find an existing socket connection
        newly_created = False

        # It's not valid to not have a socket and a readonly pool
        if self.readonly and not client_socket:
            raise Exception("SocketPool is read only and we're trying to fetch a non-existing socket")
        
        if not client_socket: # If we didn't find one, create one
            receiver = (socket_host, socket_port)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	    # Enable TCP_NODELAY to improve performance of sending one-off packets by
	    # immediately acknowledging received packages instead of trying to
	    # piggyback the ACK on the next outgoing packet (Nagle's algorithm)
	    # XXX: If you remove this, remember to do so in utils as well.
            client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) # Testing with Nagle off
            
            client_socket.connect( receiver )
            # DEBUG - TESTING SOCKET OPTIONS
            #print "OPTIONS"
            #print str(client_socket.getsockopt(socket.SOL_TCP,socket.SOCK_STREAM))
            #print str(client_socket.getsockopt(socket.SOL_TCP,socket.AF_INET))
            #print "NODELAY:" + str(client_socket.getsockopt(socket.SOL_TCP,socket.TCP_NODELAY))
            ##client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            #print "NODELAY:" + str(client_socket.getsockopt(socket.SOL_TCP,socket.TCP_NODELAY))
            
            if len(self.sockets) >= self.max_size: # Throw one out if there are too many
                Logger().debug("Socket pool LIMIT (%i) reached, throwing one out" % self.max_size)
                self._remove_element()
                
            # Add the new socket to the list
            self._add(rank, client_socket, force_persistent)
            newly_created = True
            
        #Logger().debug("SocketPool.get_socket (read-only:%s): Created (%s) socket connection for rank %d: %s" % (self.readonly,newly_created, rank, client_socket))
        return client_socket, newly_created
    
    def add_accepted_socket(self, socket_connection, global_rank):
        """
        Add a socket connection to the pool, where the connection is the returned
        value from a socket.accept - that is we are at the recieving end of a
        connection attempt.
        """        
        if self.readonly:
            # DEBUG
            #Logger().debug("Bad conn to rank %i with metainfo:%s and sockets:%s" % (global_rank, self.metainfo, self.sockets))
            raise Exception("Can't add accepted socket. We're in readonly mode")        

        #Logger().debug("SocketPool.add_accepted_socket: Adding socket connection for rank %d: %s" % (global_rank, socket_connection))
        known_socket = self._get_socket_for_rank(global_rank)
        
        if known_socket == socket_connection:
            Logger().error("SocketPool.add_accepted_socket: Trying to add a socket_connection that is already in the pool?!")
            return
        
        if known_socket:
            # When two procs send to each other simultaneously the result can be
            # adding a duplicate connection
            #Logger().debug("Already a socket in the pool:%s for an accepted connection:%s to rank:%i" % (known_socket,socket_connection,global_rank))
            pass
        
        
        if len(self.sockets) >= self.max_size: # Throw one out if there are too many
                Logger().debug("Socket pool LIMIT (%i) reached, throwing one out" % self.max_size)
                self._remove_element()
                
        self._add(global_rank, socket_connection, False)
    
    def _remove_element(self):
        """
        Finds the first element that already had its second chance and
        remove it from the list.
        
        NOTE:
        We don't explicitly close the socket once removed. Or remove it from the
        socket_to_request dict.
        This has nothing to do with correctness but it is wasteful and we should
        clean up after ourselves.
        See also issue #13 Socket pool does not limit connections properly
        """
        foundOne = False
        with self.sockets_lock:
            for client_socket in self.sockets:
                (srank, referenced, force_persistent) = self.metainfo[client_socket]
                if force_persistent: # We do not remove persistent connections
                    Logger.debug("FOUND A PERSISTENT ONE!")
                    continue
                
                if referenced: # Mark second chance
                    self.metainfo[client_socket] = (srank, False, force_persistent)
                else: # Has already had its second chance
                    self.sockets.remove(client_socket) # remove from socket pool
                    del self.metainfo[client_socket] # delete metainfo
                    foundOne = True
                    break
            
            # If a pass found nothing to remove we take the first non-persistent
            if not foundOne:
                for client_socket in self.sockets:
                    (srank, referenced, force_persistent) = self.metainfo[client_socket]
                    if force_persistent: # skip persistent connections
                        continue
                    else:
                        self.sockets.remove(client_socket) # remove from socket pool
                        del self.metainfo[client_socket] # delete metainfo
                        foundOne = True
                        break
                    
                # If we still didn't find one, they must all have been persistant
                if not foundOne:
                    # Alert the user, harshly
                    raise MPIException("Not possible to add a socket connection to the internal caching system. There are %d persistant connections and they fill out the cache" % self.max_size)
    
    def _get_socket_for_rank(self, rank):
        """
        Attempts to find an already created socket with a connection to a
        specific rank. If this does not exist we return None
        """
        #Logger().debug("SocketPool._get_socket_for_rank: Trying to fetch socket for rank %d" % rank)
        for client_socket in self.sockets:
            (srank, referenced, fp) = self.metainfo[client_socket]
            if srank == rank:
                self.metainfo[client_socket] = (srank, True, fp)
                return client_socket
        
        return None
    
    def _add(self, rank, client_socket, force_persistent):
        #Logger().debug("SocketPool._add: for rank %d: %s" % (rank, client_socket))
        with self.sockets_lock:
            self.metainfo[client_socket] = (rank, False, force_persistent)
            self.sockets.append(client_socket)
                
    def close_all_sockets(self):
        """
        Close all sockets in the socketpool
        """        
        for s in self.sockets:            
            try:
                #s.shutdown(2)
                s.close()                
            except Exception, e:
                Logger().debug("Got error when closing socket: %s" % e)
