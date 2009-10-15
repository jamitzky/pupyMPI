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
        if not client_socket: # If we didn't find one, create one
            receiver = (socket_host, socket_port)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect( receiver )
            
            if len(self.sockets) > self.max_size: # Throw one out if there are too many
                self._remove_element()
                
            # Add the new socket to the list
            self._add(rank, client_socket, force_persistent)
            newly_created = True
        Logger().debug("SocketPool: Created (%s) socket connection for rank %d: %s" % (newly_created, rank, client_socket))
        return client_socket, newly_created
    
    def add_created_socket(self, socket_connection, global_rank):
        Logger().debug("SocketPool: Adding socket connection for rank %d: %s" % (global_rank, socket_connection))
        known_socket = self._get_socket_for_rank(global_rank)
        
        if known_socket == socket_connection:
            Logger().warning("We were very close to pushing a socket out and putting it in again. BAD")
            return
        
        if known_socket:
            Logger().warning("There is already a socket in the pool for a created connection.. Possible loop stuff.. ")
            
        if len(self.sockets) > self.max_size: # Throw one out if there are too many
                self._remove_element()
                
        self._add(global_rank, socket_connection, False)
    
    def _remove_element(self):
        """
        Finds the first element that already had it's second chance and
        remove it from the list.
        
        NOTE: Shouldn't we close the socket we are removing here?
        NOTE-ANSWER: Yes.. maybe.. but that will not improve correctness
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
    
