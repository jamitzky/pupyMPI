import threading, time

from mpi import constants
from mpi.request import BaseRequest, Request
from mpi.exceptions import MPIException
from mpi.logger import Logger

identity = lambda x : x

class CollectiveRequest(BaseRequest):

    def __init__(self, tag, communicator, data=None, root=0):
        # Note about the super types. How about we define them depending on how many 
        # participants get the data? Or just remove them alltoghter. Added a reduce
        # for now just to handle the allreduce implementation.
        super(CollectiveRequest, self).__init__()

        self.communicator = communicator
        self.tag = tag
        self.initial_data = data

        self.root = root

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

        Logger().debug("CollectiveRequest object created for communicator %s" % self.communicator.name)

    def two_way_tree_traversal(self, tag, root=0, initial_data=None, up_func=None, down_func=None, start_direction="down", return_type='first'):
        def traverse(nodes_from, nodes_to, data_func, initial_data, pack=True):
            Logger().debug("""
            Starting a traverse with:
            \tNodes from: %s
            \tNodes to: %s
            \tInitial data: %s
            \tPack: %s
            """ % (nodes_from, nodes_to, initial_data, pack))
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
                for data_item in data:
                    data_list.append(data_item)
            
            Logger().debug("Received data for traverse (first round: %s): %s" % (pack, data_list))


            # Aggreate the data list to a single item (maybe?). The data list
            # should probably we curried with the sender rank for operations 
            # like Allgatherv
            #
            # The following lines is a bit of a hack. When we pack data, wrap it in 
            # lists should be through over.  
            if pack:
                d = {'rank' : self.communicator.rank(), 'value' : initial_data }
            else:
                d = initial_data
                
            if initial_data:
                if pack:
                    data_list.append(d)
                else:
                    data_list = d
            
            if not data_list:
                data_list = d
            
            data = data_func(data_list)

            # Send the data upwards in the tree. 
            for rank in nodes_to:
                self.communicator.send(rank, data, tag)

            Logger().debug("Return data for traverse (first round: %s): %s" % (pack, data))
            return data

        def start_traverse(direction, tree, data=None, first=True):
            if direction == "up":
                nodes_from = tree.down
                nodes_to = tree.up
            else:
                nodes_from = tree.up
                nodes_to = tree.down
            
            if not first and nodes_from:
                # In the second way down we should only use the data
                # from the first run if we were the last nodes in the
                # tree. That is the "not first" logic is to ensure
                # we're on the second iteration and "nodes_from" mean
                # we were not the last nodes.
                data = None
            
            return traverse(nodes_from, nodes_to, up_func, data, pack=first)

        # Creates reasonable defaults 
        if start_direction == "down":
            end_direction = "up"
        else:
            end_direction = "down"
            
        # Step 1: Setup safe methods for propergating data through the tree if
        #         the callee didn't give us any.
        #up_func = up_func or CollectiveRequest.Datafunctions.safehead
        down_func = down_func or identity
        up_func = up_func or identity

        # Step 2: Find a broadcast tree with the proper root. The tree is 
        #         aware of were we are :)
        tree = self.communicator.get_broadcast_tree(root=root)
        Logger().debug("collectiverequest.two_way_tree_traversal: Before the first way. Got bc_tree for root %d: %s" % (root, tree))

        # Step 3: Traverse the tree in the first direction. 
        rt_first = start_traverse(start_direction, tree, initial_data)
        
        if self.communicator.rank() == tree.root:
            Logger().debug("Root of the tree got a list with %d elements: %s" % (len(rt_first), rt_first))
            
        Logger().debug("collectiverequest.two_way_tree_traversal: After the first way")

        # Step 4: Run the other direction. This should also just have been
        #         done in the same if as before, but I seperated the cases
        #         because I think we can get some performance out if we 
        #         do stuff right here (ie. this is no correct yet). Is there
        #         any reason we need to traverse the entire tree in one 
        #         direction before we can start the second traversal?
        rt_second = start_traverse(end_direction, tree, rt_first, first=False)

        Logger().debug("collectiverequest.two_way_tree_traversal: After the second way")

        if return_type == 'first':
            return rt_first
        else:
            return rt_second

    def start_barrier(self):
        self.two_way_tree_traversal(self.tag)

    def start_bcast(self):
        data = self.two_way_tree_traversal(self.tag, root=self.root, initial_data=self.initial_data)
        
        # The result of a broadcast will be a list with one element which is a 
        # dict. It's a list of length one as we do not give a function so it
        # defaults to safeheade -> (None | [ element ])
        Logger().warn("Broadcast data from two_way_tree: %s" % data)
        self.data = data.pop()['value']

    def start_allreduce(self, operation):
        """
        Take a tree containing all the nodes. We start from the bottom up doing the
        operation collecting the final result at the root of the node. This decudes that

            up_func = operation
            start_direction = up

        We then take the result and pass it though to the nodes. This gives:

            down_func = id = None
            return_type = 'last'
        """
        
        self.data = self.two_way_tree_traversal(self.tag, initial_data=self.initial_data, 
                    up_func=operation, start_direction="up", return_type="last")

    def start_alltoall(self):
        # Make the inner functionality append all the data from all the processes
        # and return it. We'll just extract the data we need. 
        data = self.two_way_tree_traversal(self.tag, initial_data=self.initial_data, start_direction="up", return_type="last")
        
        Logger().info("Received data: %d: %s" % (len(data), data))
        
        # The data is of type { <rank> : [ data0, data1, ..dataS] }. We extract
        # the N'th data in the inner list where N is our rank
        rank = self.communicator.rank()
        size = self.communicator.size()
        final_data = [None for x in range(size)]

        for item in data:
            sender_rank = item['rank']
            final_data[item['rank']] = item['value'][rank]
        
        self.data = final_data

    def cancel(self):
        """
        Cancel a request. This can be used to free memory, but the request must be redone
        by all parties involved.
        
        http://www.mpi-forum.org/docs/mpi-11-html/node50.html
        """
        # We just set a status and return right away. What needs to happen can be done
        # at a later point
        self._metadata['status'] = 'cancelled'
        Logger().debug("Cancelling a request with tag" % self.tag)
        

    def get_status(self):
        return self._metadata['status']

    def wait(self):
        """
        Returns data if there are anything. This method should be rewritten to
        handle stuff like locking, proper waiting for some signal that the
        request is finished. 
        """
        return getattr(self, "data", None)
        
