import threading, time

from mpi import constants
from mpi.request import BaseRequest, Request
from mpi.exceptions import MPIException
from mpi.logger import Logger

identity = lambda x : x

class CollectiveRequest(BaseRequest):

    def __init__(self, tag, communicator, data=None, root=0, start=True):
        # Note about the super types. How about we define them depending on how many 
        # participants get the data? Or just remove them alltoghter. Added a reduce
        # for now just to handle the allreduce implementation.
        super(CollectiveRequest, self).__init__()

        self.communicator = communicator
        self.tag = tag
        self.initial_data = data
        self.root = root
        self.start = start

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
        
        if start:
            self.data = self.two_way_tree_traversal()

    def two_way_tree_traversal(self, up_func=None, down_func=None, start_direction="down", return_type='first'):
        def traverse(direction, nodes_from, nodes_to, data_func, initial_data, iteration=1):
            Logger().debug("""
            Starting a traverse with:
            \tNodes from: %s
            \tNodes to: %s
            \tInitial data: %s
            \tIteration: %d
            """ % (nodes_from, nodes_to, self.initial_data, iteration))
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
                handle = self.communicator.irecv(rank, self.tag)
                request_list.append(handle)

            for handle in request_list:
                data = handle.wait()
                if data and isinstance(data, list):
                    for data_item in data:
                        data_list.append(data_item)
                else:
                    data_list.append(data)
             
            Logger().debug("Received data for traverse (iteration: %d): %s" % (iteration, data_list))

            if iteration == 1:
                # First iteration should do something with our data
                # and pass the result further.
                d = {'rank' : self.communicator.rank(), 'value' : initial_data }

                if initial_data is not None:
                    data_list.append(d)
                
                # We look at the operations settings to check if we should run the
                # data_func or wait until all the operations has gathered.
                partial_data = getattr(data_func, "partial_data", False)
                if partial_data:
                    # Look if we should give the data function all the information
                    # like rank, or just the plain numbers.
                    full_meta = getattr(data_func, "full_meta", False)
                    
                    if not full_meta:
                        data_list =  [x['value'] for x in data_list]
                
                    data_list = {'rank' : self.communicator.rank(), 'value' : data_func(data_list) }
                    
            elif iteration == 2:
                # Second iteration should just pass the data through the pipeline
                # we might develop something more clever here to enable filtering
                # the data so we pass lesser data on the wire.
                d = initial_data
                if not data_list:
                    data_list = d

            else:
                raise Exception("Collective request got invalid iteration: %s" % iteration)
            
            # Pack the data a special way so we can put it into the right stucture later
            # on. 
             
            for rank in nodes_to:
                self.communicator.send(rank, data_list, self.tag)

            return data_list

        def start_traverse(direction, tree, data=None, iteration=1):
            if direction == "up":
                nodes_from = tree.down
                nodes_to = tree.up
                
                if iteration == 1:
                    operation = up_func
                else:
                    operation = down_func
                
            else:
                nodes_from = tree.up
                nodes_to = tree.down

                if iteration == 2:
                    operation = up_func
                else:
                    operation = down_func
                
            if iteration == 2 and nodes_from:
                # In the second way down we should only use the data
                # from the first run if we were the last nodes in the
                # tree. That is the "not first" logic is to ensure
                # we're on the second iteration and "nodes_from" mean
                # we were not the last nodes.
                data = None
            
            return traverse(direction, nodes_from, nodes_to, operation, data, iteration=iteration)

        # Creates reasonable defaults 
        if start_direction == "down":
            end_direction = "up"
        else:
            end_direction = "down"
            
        # Step 1: Setup safe methods for propergating data through the tree if
        #         the callee didn't give us any.
        down_func = down_func or identity
        up_func = up_func or identity

        # Step 2: Find a broadcast tree with the proper root. The tree is 
        #         aware of were we are :)
        tree = self.communicator.get_broadcast_tree(root=self.root)
        Logger().debug("collectiverequest.two_way_tree_traversal: Before the first way. Got bc_tree for root %d: %s" % (self.root, tree))

        # Step 3: Traverse the tree in the first direction. 
        rt_first = start_traverse(start_direction, tree, self.initial_data)
        
        Logger().debug("collectiverequest.two_way_tree_traversal: After the first way")

        # Step 4: Run the other direction. This should also just have been
        #         done in the same if as before, but I seperated the cases
        #         because I think we can get some performance out if we 
        #         do stuff right here (ie. this is no correct yet). Is there
        #         any reason we need to traverse the entire tree in one 
        #         direction before we can start the second traversal?
        rt_second = start_traverse(end_direction, tree, rt_first, iteration=2)

        Logger().debug("collectiverequest.two_way_tree_traversal: After the second way")

        if return_type == 'first':
            return rt_first
        else:
            return rt_second

    def start_bcast(self):
        """
        Creates a custom down function that will ensure only one item
        is sent through the tree. 

        The up message is irrelevant. It's only there to ensure the 
        blocking requirement.
        """
        def down_identity_func(input_list):
            if input_list: 
                return input_list.pop()
        down_identity_func.partial_data = True

        data = self.two_way_tree_traversal(start_direction="down", return_type="first", down_func=down_identity_func)

        self.data = data['value']

    def start_allgather(self):
        data = self.two_way_tree_traversal(start_direction="up", return_type="last")
        final_data = range(self.communicator.size())
        for item in data:
            try:
                final_data[item['rank']] = item['value']
            except TypeError, e:
                Logger().error("item %s of data %s" % (item, data) )
                raise TypeError("item %s of data %s" % (item, data) )
        
        self.data = final_data

    def start_scan(self, operation):
        data = self.two_way_tree_traversal(start_direction="up", return_type="last")
        
        our_data = []
        our_rank = self.communicator.rank()
        
        for item in data:
            if item['rank'] <= our_rank:
                our_data.append(item)

        # Look into the operation
        full_meta = getattr(operation, "full_meta", False)
        if not full_meta:
            our_data =  [x['value'] for x in our_data]
                
        # Apply the operation on the data.
        self.data = operation(our_data) 

    def start_allreduce(self, operation):
        self.data = self.two_way_tree_traversal(up_func=operation, start_direction="up", return_type="last")
        
        # FIXME: Currently we're looking at the type of self.data as the collective
        # operations will wrap things in to many lists. We need some way to ensure
        # this does not happen. Also to test the system with lists as the primary 
        # datatype, as our system might crash on this. 

        partial_data = getattr(operation, "partial_data", False)
        if not partial_data:
            full_meta = getattr(operation, "full_meta", False)
            
            if not full_meta:
                self.data = [x['value'] for x in self.data]
        
            self.data = operation(self.data) 
        else:
            if isinstance(self.data, list):
                self.data = self.data.pop()['value']
            else:
                self.data = self.data['value']
        
    def start_alltoall(self):
        self.data = self.two_way_tree_traversal(start_direction="up", return_type="last")

        # Make the inner functionality append all the data from all the processes
        # and return it. We'll just extract the data we need. 
        Logger().info("Received data: %d: %s" % (len(self.data), self.data))
        
        # The data is of type { <rank> : [ data0, data1, ..dataS] }. We extract
        # the N'th data in the inner list where N is our rank
        rank = self.communicator.rank()
        size = self.communicator.size()
        final_data = [None for x in range(size)]

        for item in self.data:
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
        
