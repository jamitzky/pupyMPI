# Fred dabbling in communication
from mpi.exceptions import MPINoSuchRankException
from mpi.logger import Logger

class Communicator:
    def __init__(self, rank, size, mpi_instance, name="MPI_COMM_WORLD"):
        self._rank = rank
        self._size = size
        self.name = name
        self.members = {}
        self.attr = {}
        if name == "MPI_COMM_WORLD":
            self.attr = {   "MPI_TAG_UB": 2**30, \
                            "MPI_HOST": "TODO", \
                            "MPI_IO": rank, \
                            "MPI_WTIME_IS_GLOBAL": False
                        }
    
    def build_world(self, all_procs):
        logger = Logger()
        for (hostname, port_no, rank) in all_procs:
            self.members[ rank ] = (hostname, port_no)
            logger.debug("Added proc-%d with info (%s,%s) to the world communicator" % (rank, hostname, port_no))

    def __repr__(self):
        return "<Communicator %s with %d members>" % (self.name, self.size)

    def have_rank(self, rank):
        return rank in self.members
    
    def get_network_details(self, rank):
        if not self.have_rank(rank):
            raise MPINoSuchRankException()

        return self.members[rank]
    
    def rank(self):
        return self._rank

    def size(self):
        return self._size

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    # TODO: may want to drop this and simply allow users access to the underlying dict?
    # TODO: Global fixed keys (http://www.mpi-forum.org/docs/mpi-11-html/node143.html) should be defined?
    def attr_get(self, key):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html, python-style:
        keyval is now any immutable datatype, and flag is not used. If the key is not defined, None is returned. """
        return self.attr[key]
    def attr_put(self, key, value):
        """Implements http://www.mpi-forum.org/docs/mpi-11-html/node119.html"""
        self.attr[key] = value   
        

    ################################################################################################################
    # NETWORK OPERATIONS
    ################################################################################################################
    
    # deliberately skipped:
    # 
    # due to having to do with data types or memory management:
    # mpi_address
    #
    # due to making no sense in a python environment:
    # bsend, ibsend
    # rsend, irsend
    #

    # Some wrapper methods
    def isend(self, destination, content, tag):
        """
        document me
        """
        return self.network.isend(destination, content, tag, self)

    def send(self, destination, content, tag):
        """
        document me
        """
        request = self.isend(destination, content, tag, self)
        return request.wait()

    def barrier(self):
        """
        document me
        """
        Logger().warn("Non-Implemented method 'Barrier' called.")
        return self.network.barrier(self)

    def recv(self, destination, tag):
        """
        document me
        """
        request = self.irecv(destination, tag, self)
        return request.wait()

    def irecv(self, destination, tag):
        """
        document me
        """
        return self.network.irecv(destination, tag, self)
     
    def abort(self, arg):
        """
        This routine makes a "best attempt" to abort all tasks in the group of comm.
        http://www.mpi-forum.org/docs/mpi-11-html/node151.html
            // Example C code
            #include <mpi.h>
            int main(int argc, char *argv[])
            {
                MPI_Init(NULL, NULL);
                MPI_Abort(MPI_COMM_WORLD, 911);
                /* No further code will execute */
                MPI_Finalize();
                return 0;
            }
        """
        Logger().warn("Non-Implemented method 'abort' called.")

    def allgather(self, sendbuf, sendcount, recvcount):
        """
        MPI_ALLGATHER can be thought of as MPI_GATHER, but where all processes receive the result, instead of just the root. 
        The block of data sent from the jth process is received by every process and placed in the jth block of the buffer recvbuf. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node73.html#Node73
        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allgather.html        
        """
        # TODO return recvbuf
        Logger().warn("Non-Implemented method 'allgather' called.")

    def allgatherv(self, sendbuf, sendcount, recvcount, displs):
        """
        MPI_ALLGATHERV can be thought of as MPI_GATHERV, but where all processes receive the result, instead of just the root. The  jth block of data sent from each process is received by every process and placed in the  jth block of the buffer recvbuf. These blocks need not all be the same size. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node73.html#Node73
        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allgatherv.html        
        """
        # TODO return recvbuf
        Logger().warn("Non-Implemented method 'allgatherv' called.")

    def allreduce(self, sendbuf, recvbuf, count, op):
        """
        Same as MPI_REDUCE except that the result appears in the receive buffer of all the group members.

        http://www.mpi-forum.org/docs/mpi-11-html/node82.html        
        Examples: http://mpi.deino.net/mpi_functions/MPI_Allreduce.html
        """
        Logger().warn("Non-Implemented method 'allreduce' called.")
        
    def alltoall(self, sendbuf, sendcount, recvbuf, recvcount):
        """
        IN sendbuf starting address of send buffer (choice) 
        IN sendcount number of elements sent to each process (integer) 
        IN recvcount number of elements received from any process (integer) 
        IN comm communicator (handle) 
        OUT recvbuf address of receive buffer (choice) 
        
        MPI ALLTOALL is an extension of MPI ALLGATHER to the case where each process 
        sends distinct data to each of the receivers. The jth block sent from process i is received 
        by process j and is placed in the ith block of recvbuf...
        
        http://www.mpi-forum.org/docs/mpi-11-html/node75.html
        Example: http://mpi.deino.net/mpi_functions/MPI_Alltoall.html
        """

        Logger().warn("Non-Implemented method 'alltoall' called.")
        
    def alltoallv(self, sendbuf, sendcount, sdispls, recvbuf, recvcount, rdispls):
        """
        IN sendbuf starting address of send buffer (choice) 
        IN sendcounts integer array equal to the group size specifying the number of elements to send to each processor 
        IN sdispls integer array (of length group size). Entry j specifies the displacement (relative to sendbuf from which to take the outgoing data destined for process j 
        IN sendtype data type of send buffer elements (handle) 
        OUT recvbuf address of receive buffer (choice) 
        IN recvcounts integer array equal to the group size specifying the number of elements that can be received from each processor 
        IN rdispls integer array (of length group size). Entry i specifies the displacement (relative to recvbuf at which to place the incoming data from process i) 
        
        MPI_ALLTOALLV adds flexibility to MPI_ALLTOALL in that the location of data for the send is specified by sdispls
        and the location of the placement of the data on the receive side is specified by rdispls. 
        
        http://www.mpi-forum.org/docs/mpi-11-html/node75.html    
        """
        
        Logger().warn("Non-Implemented method 'alltoallv' called.")
        
    def bcast(self, buffer, count, root):
        """
        INOUT buffer starting address of buffer (choice) 
        IN count number of entries in buffer (integer) 
        IN datatype data type of buffer (handle) 
        IN root rank of broadcast root (integer) 
        IN comm communicator (handle) 

        MPI BCAST broadcasts a message from the process with rank root to all processes of 
        the group, itself included. It is called by all members of group using the same arguments 
        or comm, root. On return, the contents of root's communication buffer has been copied to all processes. 

        http://www.mpi-forum.org/docs/mpi-11-html/node67.html
        """
    
        Logger().warn("Non-Implemented method 'bcast' called.")
