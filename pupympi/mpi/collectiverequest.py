import threading, time

from mpi import constants
from mpi.request import BaseRequest, Request
from mpi.exceptions import MPIException
from mpi.logger import Logger

class CollectiveRequest(BaseRequest):

    def __init__(self, request_type, communicator, data=None, root=0):
        super(CollectiveRequest, self).__init__()
        if request_type not in ('barrier', 'bcast', 'comm_create','comm_free'): # TODO more needed here
            raise MPIException("Invalid type in collective request creation. This should never happen. ")

        self.request_type = request_type
        self.communicator = communicator

        # Meta information we use to keep track of what is going on. There are some different
        # status a request object can be in:
        # 
        # 'new' ->         The object is newly created. If this is send the lower layer can start to 
        #                  do stuff with the data
        #                  'cancel' is not valid for collective ops: all are blocking.(NBC in mpi2 also cannot be cancelled)
        # 'inprogress' ->  Collective request is in progress but nothing new on the wire
        # 'ready'     ->   Means we have the data (in receive) or pickled the data (send) and can
        #                  safely return from a test or wait call.
        self._m = {'status' : 'new' }

        Logger().debug("CollectiveRequest object created for communicator %s and type %s" % (self.communicator.name, self.request_type))

        if self.request_type == "bcast":
            self.start_bcast(root, data)

        if self.request_type == 'barrier':
            self.start_barrier()

    def two_way_tree_traversal(self, tag, root=0, initial_data=None, up_func=None, down_func=None, start_direction="down", return_type='first'):
        def safehead(data_list):
            if data_list:
                return data_list.pop()
            else:
                return None
    
        def traverse(nodes_from, nodes_to, data_func, initial_data):
            # If The direction is up, so we find the result of all our children
            # and execute som function on these data. The result of the function
            # is passed on to our parent. The result is also returned from the
            # function, and if this is the last direction in the traversal the
            # callee will get the data. 
            data_list = []

            # When receiving from N people, we're making them non-blocking so
            # we can receive data while we wait for the last one. It might make
            # sense to already start the receiving calls in the other direction?
            request_list = []
            
            for rank in nodes_from:
                handle = self.communicator.irecv(rank, tag)
                request_list.append(handle)

            for handle in request_list:
                data = handle.wait()
                data_list.append(data)

            # Aggreate the data list to a single item (maybe?). The data list
            # should probably we curried with the sender rank for operations 
            # like Allgatherv
            if data_list:
                data = data_func(data_list)
            else:
                data = initial_data

            # Send the data upwards in the tree. 
            for rank in nodes_to:
                self.communicator.send(rank, data, tag)

            return data

        def up(data=None):
            return traverse(tree.down, tree.up, up_func, data)

        def down(data=None):
            return traverse(tree.up, tree.down, down_func, data)

        # Step 1: Setup safe methods for propergating data through the tree if
        #         the callee didn't give us any.
        if not up_func:
            up_func = safehead

        if not down_func:
            down_func = safehead

        # Step 2: Find a broadcast tree with the proper root. The tree is 
        #         aware of were we are :)
        tree = self.communicator.get_broadcast_tree(root=root)

        # Step 3: Traverse the tree in the first direction. 
        if start_direction == "down":
            rt_first = down(initial_data)
            other = up
        else:
            rt_first = up(initial_data)
            other = down

        # Step 4: Run the other direction. This should also just have been
        #         done in the same if as before, but I seperated the cases
        #         because I think we can get some performance out if we 
        #         do stuff right here (ie. this is no correct yet). Is there
        #         any reason we need to traverse the entire tree in one 
        #         direction before we can start the second traversal?
        rt_second = other()

        if return_type == 'first':
            return rt_first
        else:
            return rt_second

    def start_barrier(self):
        self.two_way_tree_traversal(constants.TAG_BARRIER)

    def start_bcast(self, root, data):
        self.data = self.two_way_tree_traversal(constants.TAG_BCAST, root=root, initial_data=data)

    def network_callback(self, lock=True, *args, **kwargs):
        Logger().debug("Network callback in request called")

        if lock:
            self.acquire()

        # FIXME: Handle stuff in here.. DO IT
            
        if lock:
            self.release()

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self._m['status'] = 'cancelled'
        Logger().debug("Cancelling a %s request" % self.request_type)
        

    # FIXME Deleted test and wait until we know if they'll be needed (copy from Request then)

    def get_status(self):
        return self._m['status']

    def wait(self):
        """
        Returns data if there are anything. This method should be rewritten to
        handle stuff like locking, proper waiting for some signal that the
        request is finished. 
        """
        return getattr(self, "data", None)
        
