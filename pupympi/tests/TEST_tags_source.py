#!/usr/bin/env python2.6

# Simple pupympi program to test if tags are handled correctly
# rank 0 sends 5 messages to rank 1 which should receive the first 3 but not the last 2.
#
# This test is meant to run with 2 processes

from mpi import MPI
from mpi import constants
import time

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


content = "MSG"

a_real_tag = 1
an_unreal_tag = 2 # not supposed to receive this

if rank == 0:
    # Send
    neighbour = 1
    print "Rank: %d sending to %d - test of any_tag, specific source" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(neighbour,content, a_real_tag)
    #print "Rank: %d sending to %d - test of any_tag, any_source" % (rank,neighbour)
    #mpi.MPI_COMM_WORLD.send(neighbour,content, a_real_tag)
    #print "Rank: %d sending to %d - test of specific tag, any_source" % (rank,neighbour)
    #mpi.MPI_COMM_WORLD.send(neighbour,content, a_real_tag)
    #print "Rank: %d sending to %d - test of unreal tag, any_source" % (rank,neighbour)
    #mpi.MPI_COMM_WORLD.send(neighbour,content, an_unreal_tag)
    #print "Rank: %d sending to %d - test of specific tag, unreal source" % (rank,neighbour)
    #mpi.MPI_COMM_WORLD.send(neighbour,content, a_real_tag)
    #

elif rank == 1: 
    # Recieve
    neighbour = 0    
    print "rank: %d recieving from %d - test of any_tag, specific source" % (rank,neighbour)
    #recieved = mpi.MPI_COMM_WORLD.recv(neighbour,constants.MPI_TAG_ANY)
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour,a_real_tag)    
    
    #print "rank: %d recieving from %d - test of any_tag, any_source" % (rank,neighbour)
    #recieved = mpi.MPI_COMM_WORLD.recv(constants.MPI_SOURCE_ANY,constants.MPI_TAG_ANY)    
    #print "Rank: %d receiving from %d - test of specific tag, any_source" % (rank,neighbour)
    #recieved = mpi.MPI_COMM_WORLD.recv(constants.MPI_SOURCE_ANY, a_real_tag)    
    #print "Rank: %d receiving from %d - test of unreal tag, any_source" % (rank,neighbour)
    #recv_handle_1 = mpi.MPI_COMM_WORLD.irecv(constants.MPI_SOURCE_ANY, a_real_tag)    
    #print "Rank: %d receiving from %d - test of specific tag, unreal source" % (rank,neighbour)
    #recv_handle_2 = mpi.MPI_COMM_WORLD.recv(1, a_real_tag)    
    #
    #print "Rank %d is now waiting 5 seconds" % rank
    #time.sleep(5)
    #print "Rank %d done waiting, now testing" % rank
    #if recv_handle_1.test() or recv_handle_2.test():
    #    raise "rank 1 received something that it shouldnt have."        
    
else:
    print "I'm rank %d and I'm not doing anything in this test" % rank

print "Rank %s All done" % rank

mpi.finalize()
