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
    
    ERRORS: It's possible to trigger an error if you fill up the cache with
    more persistent connections than the buffer can actually contain. An
    MPIException will be raised in this situation. 
    """
    
    def __init__(self, max_size):
        self.sockets = []
        self.max_size = max_size
        self.readonly = False
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
            #client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) # Testing with Nagle off
            
            client_socket.connect( receiver )
            # DEBUG - TESTING SOCKET OPTIONS
            #print "OPTIONS"
            #print str(client_socket.getsockopt(socket.SOL_TCP,socket.SOCK_STREAM))
            #print str(client_socket.getsockopt(socket.SOL_TCP,socket.AF_INET))
            #print "NODELAY:" + str(client_socket.getsockopt(socket.SOL_TCP,socket.TCP_NODELAY))
            ##client_socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            #print "NODELAY:" + str(client_socket.getsockopt(socket.SOL_TCP,socket.TCP_NODELAY))
            
            if len(self.sockets) > self.max_size: # Throw one out if there are too many
                self._remove_element()
                
            # Add the new socket to the list
            self._add(rank, client_socket, force_persistent)
            newly_created = True
        Logger().debug("SocketPool.get_socket (read-only:%s): Created (%s) socket connection for rank %d: %s" % (self.readonly,newly_created, rank, client_socket))
        return client_socket, newly_created
    
    def add_created_socket(self, socket_connection, global_rank):
        if self.readonly:
            # DEBUG
            Logger().info("Bad conn to rank %i with metainfo:%s and sockets:%s" % (global_rank, self.metainfo, self.sockets))
            raise Exception("Can't add created socket. We're in readonly mode")        

        Logger().debug("SocketPool.add_created_socket: Adding socket connection for rank %d: %s" % (global_rank, socket_connection))
        known_socket = self._get_socket_for_rank(global_rank)
        
        if known_socket == socket_connection:
            Logger().info("SocketPool.add_created_socket: We were very close to pushing a socket out and putting it in again. BAD")
            return
        
        if known_socket:
            Logger().info("There is already a socket in the pool for a created connection.. Possible loop stuff.. ")
        
        
        if len(self.sockets) > self.max_size: # Throw one out if there are too many
                self._remove_element()
                
        self._add(global_rank, socket_connection, False)
    
    def _remove_element(self):
        """
        Finds the first element that already had it's second chance and
        remove it from the list.
        
        NOTE: We don't explicitly close the socket once removed. This has nothing
        to do with correctness but we should clean up after ourselves. See issue#
        """
        with self.sockets_lock:
            for x in range(2): # Run through twice
                for client_socket in self.sockets:
                    (srank, sreference, force_persistent) = self.metainfo[client_socket]
                    if force_persistent: # We do not remove persistent connections
                        continue
                    
                    if sreference: # Mark second chance
                        self.metainfo[client_socket] = (srank, False, force_persistent)
                    else: # Has already had its second chance
                        self.sockets.remove(client_socket) # remove from socket pool
                        del self.metainfo[client_socket] # delete metainfo
                        break

        raise MPIException("Not possible to add a socket connection to the internal caching system. There are %d persistant connections and they fill out the cache" % self.max_size)
    
    def _get_socket_for_rank(self, rank):
        """
        Attempts to find an already created socket with a connection to a
        specific rank. If this does not exist we return None
        """
        #Logger().debug("SocketPool._get_socket_for_rank: Trying to fetch socket for rank %d" % rank)
        for client_socket in self.sockets:
            (srank, _, fp) = self.metainfo[client_socket]
            if srank == rank:
                self.metainfo[client_socket] = (srank, True, fp)
                return client_socket
        
        return None
    
    def _add(self, rank, client_socket, force_persistent):
        with self.sockets_lock:
            self.metainfo[client_socket] = (rank, True, force_persistent)
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
