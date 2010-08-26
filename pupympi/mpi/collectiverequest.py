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
from mpi.request import BaseRequest
from mpi.logger import Logger
from mpi import constants

# this is used when we do not want to transform the data
identity = lambda x : x

class CollectiveRequest(BaseRequest):
    """
    ISSUES:
    - "Everybody knows you don't go full_meta!" (aka. let's all find more descriptive names)
    - Collective calls in general do not have to have both up and down traversal of the tree,
      the previously perceived global blocking requirement has been deemed out by Brian(!)
    - When passing lists around in the tree they should not be flattened before it is neccessary so we avoid excessive iterating
    - We should test that the broadcast trees are indeed reused
    - When we reduce or gather we should not degrade to allreduce or alltoall and just throw away the redundant data
      instead we should make sure only the needed data is passed around the tree
    """

    def __init__(self, tag, communicator, data=None, root=0, mpi_op=None):
        super(CollectiveRequest, self).__init__()

        self.communicator = communicator
        self.tag = tag
        self.initial_data = data
        self.root = root        
        self.mpi_op = mpi_op

        # We inherit the status field from BaseRequest, there are some different
        # states a collective request object can be in:
        # 
        # 'new' ->         The object is newly created. If this is send the lower layer can start to 
        #                  do stuff with the data
        # 'ready'     ->   Means we have the data (in receive) or pickled the data (send) and can
        #                  safely return from a test or wait call.
        #
        # Note that 'cancel' is not valid for collective ops: all are blocking.
        # (NBC in mpi2 also cannot be cancelled)
        #Logger().debug("CollectiveRequest object created for communicator %s" % self.communicator.name)
        
        # Type specific start up
        if self.tag == constants.TAG_BARRIER:
            # The barrier does nothing really
            #self.data = self.two_way_tree_traversal()
            self.start_barrier()
            
        elif self.tag == constants.TAG_BCAST:
            #self.start_bcast_old()
            self.start_bcast()
            
        elif self.tag == constants.TAG_GATHER:
            # For now gather is just an all_gather where everybody but root throws away the result
            #self.start_allgather_old()
            self.start_gather()

        elif self.tag == constants.TAG_SCATTER:
            #self.data = self.two_way_tree_traversal()
            #self.start_scatter()
            self.start_scatter_filtered()

        elif self.tag == constants.TAG_REDUCE:
            # For now reduce is just an all_reduce where everybody but root throws away the result
            #self.start_allreduce_old(self.mpi_op)
            self.start_reduce(self.mpi_op)

        elif self.tag == constants.TAG_ALLGATHER:
            self.start_allgather()
            
        elif self.tag == constants.TAG_ALLTOALL:
            #self.start_alltoall_old()
            self.start_alltoall()
                        
        elif self.tag == constants.TAG_ALLREDUCE:
            #self.start_allreduce_old(self.mpi_op)
            self.start_allreduce(self.mpi_op)
            
        elif self.tag == constants.TAG_SCAN:
            self.start_scan_old(self.mpi_op)
            

    def two_way_tree_traversal(self, up_func=None, down_func=None, start_direction="down", return_type='first'):

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
            
            return self.traverse(direction, nodes_from, nodes_to, operation, data, iteration)

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
        #Logger().debug("collectiverequest.two_way_tree_traversal: Before the first way. Got bc_tree for root %d: %s" % (self.root, tree))

        # Step 3: Traverse the tree in the first direction. 
        rt_first = start_traverse(start_direction, tree, self.initial_data)
        
        #Logger().debug("collectiverequest.two_way_tree_traversal: After the first way")

        # Step 4: Run the other direction. This should also just have been
        #         done in the same if as before, but I seperated the cases
        #         because I think we can get some performance out if we 
        #         do stuff right here (ie. this is no correct yet). Is there
        #         any reason we need to traverse the entire tree in one 
        #         direction before we can start the second traversal?
        rt_second = start_traverse(end_direction, tree, rt_first, iteration=2)

        #Logger().debug("collectiverequest.two_way_tree_traversal: After the second way")

        if return_type == 'first':
            return rt_first
        else:
            return rt_second

            
    def traverse(self,direction, nodes_from, nodes_to, data_func, initial_data, iteration=1):
        #Logger().debug("""
        #Starting a traverse with:
        #\tNodes from: %s
        #\tNodes to: %s
        #\tInitial data: %s
        #\tIteration: %d
        #""" % (nodes_from, nodes_to, self.initial_data, iteration))
        
        """            
        If direction is up, we find the results of all our children and
        execute some function on this data. The result of the function is
        passed on to the parent node.
        The result is also returned from the function, and if this is the
        last direction in the traversal the caller will get the data.
        """
        data_list = [] # Holds accumulated results from child nodes

        # When receiving from N people, we're making them non-blocking so
        # we can receive data while we wait for the last one. It might make
        # sense to already start the receiving calls in the other direction?
        request_list = []
        
        for rank in nodes_from:
            handle = self.communicator.irecv(rank, self.tag)
            request_list.append(handle)
            
        # TODO: Reimplement so that lists are not flattened

        tmp_list = self.communicator.waitall(request_list)
        for data in tmp_list:
            if isinstance(data, list):
                for data_item in data:
                    data_list.append(data_item)
            else:
                data_list.append(data)

        #for handle in request_list:
        #    data = handle.wait()
        #    if data and isinstance(data, list):
        #        for data_item in data:
        #            data_list.append(data_item)
        #    else:
        #        data_list.append(data)
         
        #Logger().debug("Received data for traverse (iteration: %d): %s" % (iteration, data_list))

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
                    #Logger().warning("not full_meta and data_list:%s" % data_list)
                    data_list =  [x['value'] for x in data_list]
                    #Logger().warning("...and then data_list:%s" % data_list)

            
                data_list = {'rank' : self.communicator.rank(), 'value' : data_func(data_list) }
                #Logger().warning("finally data_list:%s" % data_list)

                
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
            self.communicator.send(data_list, rank, self.tag)

        return data_list
    
    def traverse_down(self, nodes_from, nodes_to, initial_data=None):
        """
        Send stuff unchanged down the tree
        """
        data_list = [] # Holds accumulated results from other nodes
        
        ### RECIEVE
        
        # Generate requests
        request_list = []        
        for rank in nodes_from:
            handle = self.communicator.irecv(rank, self.tag)
            request_list.append(handle)
        
        # Receive messages
        tmp_list = self.communicator.waitall(request_list)
        for data in tmp_list:
            data_list.append(data)
        
        # If we didn't get anything we are root in the tree so use initial data
        if not data_list:
            data_list.append(initial_data)
                
        ### SEND
        
        # Generate requests
        request_list = []
        for rank in nodes_to:
            handle = self.communicator.isend(data_list[0], rank, self.tag)
            request_list.append(handle)

        # Wait until they are sent
        # TODO: Check with MPI conditions and our general design, maybe we don't actually have to wait for the isends to complete
        tmp_list = self.communicator.waitall(request_list)
        
        return data_list

    def traverse_down_filtered(self, nodes_from, nodes_to, initial_data=None, descendants=[]):
        """
        Send data down the tree where filtering for appropriate descendants so
        that every leaf does not receive the whole sequence but only the relevant
        part
        """
        data_list = [ None for x in range(self.communicator.size()) ] # Holds accumulated results
        
        ### RECIEVE
        if nodes_from == []: # root gets from noone
            data_list = initial_data            
        elif len(nodes_from) == 1:
            node_from = nodes_from[0]                
            # Get data from above
            data_list = self.communicator.recv(node_from, self.tag)
        else:
            raise MPIException("More than one parent in nodes_from.")
            
        ### SEND
        
        # Generate requests
        request_list = []
        i = 0 # index into descendants matching nodes_to
        for rank in nodes_to:
            filtered_data_list = [ None for x in range(self.communicator.size()) ]
            filtered_data_list[rank] = data_list[rank]
            
            # NOTE: for a leaf node this would give index error but a leaf node has empty nodes_to and so this is safe
            for desc in descendants[i]:
                filtered_data_list[desc] = data_list[desc]
                
            handle = self.communicator.isend(filtered_data_list, rank, self.tag)
            request_list.append(handle)
            
            if self.communicator.rank() == self.root:
                Logger().debug("filtered:%s, nodes_from:%s, nodes_to:%s, descendants[i]:%s" % (filtered_data_list,nodes_from, nodes_to, descendants[i]))

            i += 1


        # Wait until they are sent
        # TODO: Check with MPI conditions and our general design, maybe we don't actually have to wait for the isends to complete
        tmp_list = self.communicator.waitall(request_list)
        
        return data_list

    def traverse_up(self, nodes_from, nodes_to, initial_data=None, operation=None, descendants=[]):
        data_list = [ None for x in range(self.communicator.size()) ] # Holds accumulated results

        # Generate requests
        request_list = []        
        for rank in nodes_from:
            handle = self.communicator.irecv(rank, self.tag)
            request_list.append(handle)
        
        # Receive messages from children
        tmp_list = self.communicator.waitall(request_list)
        i = 0 # index
        # Store messages from children
        for data in tmp_list:
            rank = nodes_from[i] # index into nodes_from to get the rank corresponding to the message                        
            data_list[rank] = data[rank] # put into right place (globally rank ordered)
            
            # Store descendant's messages
            desc = descendants[i]
            for d in desc:
                data_list[d] = data[d] # put into right place (globally rank ordered)
                
            i += 1
        
        # Add own data to message
        data_list[self.communicator.rank()] = initial_data # put into right place (globally rank ordered)
        
        # Pass on the data
        for rank in nodes_to:
            self.communicator.send(data_list, rank, self.tag)
        
        return data_list

    def start_barrier(self):
        """
        Wait until all processes has issued this call.
        
        TODO: Make the up traverse not care about message placement and transport
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        results = self.traverse_up(nodes_from, nodes_to, operation=None, initial_data=None, descendants=descendants)
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=None)
        
        self.data = "GO!"


    def start_bcast(self):
        """
        Send a message down the tree
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=self.initial_data)
        
        Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        
        #Logger().debug("descendants:%s" % (tree.descendants))
        # Done
        self.data = results[0] # They should all be equal so just get the first one


    def start_scatter_filtered(self):
        """
        Scatter a message in N parts to N processes
        
        TODO: We should filter such that only parts needed further down in the
              tree are passed on, instead of the whole shebang as we do now.
        """
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        descendants = tree.descendants
        results = self.traverse_down_filtered(nodes_from, nodes_to, initial_data=self.initial_data, descendants=descendants)
        
        #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        #Logger().debug("descendants:%s" % (tree.descendants))
        
        chunk_size = len(results) / self.communicator.size()
        rank = self.communicator.rank()
        self.data =  results[rank*chunk_size:(rank+1)*chunk_size] # get the bit that should be scattered to this rank (rest are Nones anyway)

    def start_scatter(self):
        """
        Scatter a message in N parts to N processes
        
        TODO: We should filter such that only parts needed further down in the
              tree are passed on, instead of the whole shebang as we do now.
        """
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=self.initial_data)
        
        #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        #Logger().debug("descendants:%s" % (tree.descendants))
        
        whole_set = results[0] # They should all be equal so just get the first one
        chunk_size = len(whole_set) / self.communicator.size()
        rank = self.communicator.rank()
        self.data =  whole_set[rank*chunk_size:(rank+1)*chunk_size] # get the bit that should be scattered to this rank
        
    def start_gather(self):
        """
        Gather a message in N parts from N processes        
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        results = self.traverse_up(nodes_from, nodes_to, operation=None, initial_data=self.initial_data, descendants=descendants)
        
        #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        
        self.data = results
        
    
    def start_reduce(self, operation):
        """
        Reduce N sequences of M elements (normally at least one element per sequence)
        with a chosen reduction operation to one sequence of M elements.
        Alternatively reduce N elements to one element.
        
        If partial reduction is allowed we partially reduce along the way in the
        tree. Otherwise all sequences are joined in order and the reduction applied
        to the final sequence.
        
        When reducing sequences they must all be of same length since reduction
        is done element-wise and the result is a sequence of the same length.
        
        When reducing a single string it will be treated as an iterable (list of
        chars), if the user wishes to treat it as an immutable single entity the
        string needs to be supplied in a singleton list.
        
        Reducing an empty sequence - eg. "" or [] - will return the same type.
        
        ISSUES:
         - Need to decide if we will allow sets and other iterables
         - Need validation on sequences being of equal length and type but maybe better to just catch all possible errors.
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree(root=self.root)
        
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        results = self.traverse_up(nodes_from, nodes_to, operation=operation, initial_data=self.initial_data, descendants=descendants)
        
        # If root reduce on the results - if not nevermind data is discarded later
        if self.communicator.rank() == self.root:
            # If it is a sequence of elements use elementwise reduction
            # (only list and string for now...)
            if isinstance(results[0],list):
                reduced_results = self._reduce_elementwise(results,operation)
            elif isinstance(results[0],str):
                char_list = self._reduce_elementwise(results,operation)
                reduced_results = ''.join(char_list) # join chars into string
            else:
                reduced_results = operation(results)
            #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (reduced_results,nodes_from, nodes_to))
        else:
            reduced_results = None
        #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        
        self.data = reduced_results
        
    def start_alltoall(self):
        """
        Disperse N messages in N parts to N processes. The i'th process supplies the i'th part to all others.
        
        Implement as gather N*sequence to rank 0 and then bcast the lot to everyone who filters appropriately
        This way optimizations in bcast can be reused and hopefully likewise for gather or allgather
        
        TODO: Need to validate input (maybe already in the communicator) to raise error as advertised.
        """
        ### GATHERING
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree()
        
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        gathered_results = self.traverse_up(nodes_from, nodes_to, operation=None, initial_data=self.initial_data, descendants=descendants)
        
        ### REORDERING
        if self.communicator.rank() == 0:
            Logger().debug("Gathered results:%s, nodes_from:%s, nodes_to:%s" % (gathered_results,nodes_from, nodes_to))
            
            ordered_results = [ [] for _ in range(self.communicator.size()) ]
            
            for seq in gathered_results:
                i = 0
                for element in seq:
                    (ordered_results[i]).append(element)                        
                    i += 1
        else:
            ordered_results = []
        
        ### BROADCASTING
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=ordered_results)
        
        #if self.communicator.rank() == 0:
        #    Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))

        ### FILTERING
        # TODO: The [0] indexing is because the results is packed in a redundant list - fix it        
        self.data = results[0][self.communicator.rank()] # Get results for own rank
        
    """
    Gathered results:
    [['0:0', '0:1', '0:2', '0:3', '0:4', '0:5'],
    ['1:0', '1:1', '1:2', '1:3', '1:4', '1:5'],
    ['2:0', '2:1', '2:2', '2:3', '2:4', '2:5'],
    ['3:0', '3:1', '3:2', '3:3', '3:4', '3:5'],
    ['4:0', '4:1', '4:2', '4:3', '4:4', '4:5'],
    ['5:0', '5:1', '5:2', '5:3', '5:4', '5:5']]
    """
    def start_allgather(self):
        """
        Gather a message in N parts from N processes        
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree()
        
        ### GATHER AT ROOT
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        gathered_results = self.traverse_up(nodes_from, nodes_to, operation=None, initial_data=self.initial_data, descendants=descendants)
        
        #Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        
        ### BCAST FROM ROOT
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=gathered_results)
        
        Logger().debug("results:%s, nodes_from:%s, nodes_to:%s" % (results,nodes_from, nodes_to))
        
        self.data = results[0] # They should all be equal so just get the first one

    def start_allreduce(self, operation):
        """
        Reduce where reduced result is available at all nodes
        """        
        # Get a tree with proper root
        tree = self.communicator.get_broadcast_tree()
        
        ### REDUCE
        # Start sending up the tree
        nodes_from = tree.down
        nodes_to = tree.up
        descendants = tree.descendants
        results = self.traverse_up(nodes_from, nodes_to, operation=operation, initial_data=self.initial_data, descendants=descendants)
        
        # If root reduce on the results - if not nevermind data is discarded later
        if self.communicator.rank() == self.root:
            # If it is a sequence of elements use elementwise reduction
            # (only list and string for now...)
            if isinstance(results[0],list):
                reduced_results = self._reduce_elementwise(results,operation)
            elif isinstance(results[0],str):
                char_list = self._reduce_elementwise(results,operation)
                reduced_results = ''.join(char_list) # join chars into string
            else:
                reduced_results = operation(results)
        else:
            reduced_results = None
        
        ### BCAST FROM ROOT
        # Start sending down the tree
        nodes_from = tree.up
        nodes_to = tree.down
        results = self.traverse_down(nodes_from, nodes_to, initial_data=reduced_results)
        
        self.data = results[0] # They should all be equal so just get the first one


    def start_scan(self, operation):
        """        
        TODO: Implement or decide to drop
        """
        raise Exception("Not implemented yet")



        ### OLD STYLE ###

    def start_bcast_old(self):
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

    def start_allgather_old(self):
        data = self.two_way_tree_traversal(start_direction="up", return_type="last")
        final_data = range(self.communicator.size())
        for item in data:
            try:
                final_data[item['rank']] = item['value']
            except TypeError:
                Logger().error("item %s of data %s" % (item, data) )
                raise TypeError("item %s of data %s" % (item, data) )
        
        self.data = final_data

    def start_scan_old(self, operation):
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

    def start_allreduce_old(self, operation):
        self.data = self.two_way_tree_traversal(up_func=operation, start_direction="up", return_type="last")
        
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
        
    def start_alltoall_old(self):
        self.data = self.two_way_tree_traversal(start_direction="up", return_type="last")

        # Make the inner functionality append all the data from all the processes
        # and return it. We'll just extract the data we need. 
        #Logger().debug("Received data: %d: %s" % (len(self.data), self.data))
        
        # The data is of type { <rank> : [ data0, data1, ..dataS] }. We extract
        # the N'th data in the inner list where N is our rank
        rank = self.communicator.rank()
        size = self.communicator.size()
        final_data = [None for _ in range(size)]

        for item in self.data:
            final_data[item['rank']] = item['value'][rank]
        
        self.data = final_data

    
    def _reduce_elementwise(self,sequences,operation):
        """
        Perform a element-wise reduction on elements of equal length sequences
        
        Sequences can be everything iterable
        """                
        # TODO: Generalize so other iterables than lists work here
        # TODO: Consider checking that all sequences are same length (max(results) = min(results))
        reduced_results = []
        no_seq = len(sequences) # How many sequences
        seq_len = len(sequences[0]) # How long is a sequence
        for i in range(seq_len):
            try:
                temp_list = [ sequences[m][i] for m in range(no_seq) ] # Temp list contains i'th element of each subsequence
            except IndexError, e:
                # If any sequence is shorter than the first one an IndexError will be raised
                print "BAD"
                raise e
                # TODO: Raise proper error here
            # Apply operation to temp list and store result
            reduced_results.append(operation(temp_list))
            
        return reduced_results


    def get_status(self):
        return self.status

    def wait(self):
        """
        Returns data if there is anything.
        
        For now this method relies on the fact that a collective request is carried
        out during the requests creation. When one gets an object to wait on, the
        data will already have been sent around.
        
        This method should probably be rewritten to handle stuff like locking, and
        proper waiting for some signal that the request is finished a la for normal
        requests.
        """
        return getattr(self, "data", None)
        
