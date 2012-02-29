#!/usr/bin/env python
# meta-description: Test allgather with repeated calls and odd communicator sizes
# meta-expectedresult: 0
# meta-minprocesses: 11
# meta-max_runtime: 25


from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

### repeated allgather calls on same communicator
for i in xrange(5):    
    received = world.allgather(rank)
    assert received == range(size)
    
    received = world.allgather(-rank)
    assert received == range(0,-size,-1)
    
    received = world.allgather(str(rank))
    assert received == [str(r) for r in range(size)]


### allgather calls on different communicators

# group of even ranks
evens = world.group().incl(range(0,size,2))
# group of odd ranks
odds = world.group().incl(range(1,size,2))
# group of lower half
lower = world.group().incl(range(size//2))

# commmunicators
evens_comm = world.comm_create(evens)
odds_comm = world.comm_create(odds)
lower_comm = world.comm_create(lower)


# post requests
if evens.rank() != -1:
    evens_handle_1 = evens_comm.iallgather((rank,rank))
    evens_handle_2 = evens_comm.iallgather((rank*2,rank*2))
    
if odds.rank() != -1:
    odds_handle_1 = odds_comm.iallgather((rank,rank))
    odds_handle_2 = odds_comm.iallgather((rank*4,rank*4))

if lower.rank() != -1:
    lower_handle_1 = lower_comm.iallgather((rank,rank))
    lower_handle_2 = lower_comm.iallgather((rank*3,rank*3))
    lower_handle_3 = lower_comm.iallgather((rank,rank,rank))


# wait in different order    
if lower.rank() != -1:
    lower_received_3 = lower_handle_3.wait()

if evens.rank() != -1:    
    evens_received_2 = evens_handle_2.wait()
    evens_received_1 = evens_handle_1.wait()
    
if odds.rank() != -1:
    odds_received_1 = odds_handle_1.wait()

if lower.rank() != -1:
    lower_received_1 = lower_handle_1.wait()
    lower_received_2 = lower_handle_2.wait()

if odds.rank() != -1:
    odds_received_2 = odds_handle_2.wait()


# asserts
if evens.rank() != -1:    
    assert evens_received_1 == [ (r,r) for r in range(0,size,2) ]
    assert evens_received_2 == [ (r*2,r*2) for r in range(0,size,2) ]
    
if odds.rank() != -1:
    assert odds_received_1 == [ (r,r) for r in range(1,size,2) ]
    assert odds_received_2 == [ (r*4,r*4) for r in range(1,size,2) ]

if lower.rank() != -1:
    assert lower_received_1 == [ (r,r) for r in range(size//2) ]
    assert lower_received_2 == [ (r*3,r*3) for r in range(size//2) ]
    assert lower_received_3 == [ (r,r,r) for r in range(size//2) ]

mpi.finalize()
