#!/usr/bin/env python2.6
# META: SKIP
# heavier-duty test

# OBSERVATIONS:
# With 2 sec padding all is ok for 250, all procs cleanly die
# With 1 sec padding not ok for 250 but we get almost halfway, sometimes all the way
# With no padding not ok for 250, we hang after first few iterations - examples below

#################### 0 sec padding
# 2009-09-30 10:59:34 proc-0      : ERROR    WELEASE WODERICK release unlocked lock
# ==> /tmp/mpi.local.rank0.log <==
# ...
# 2009-09-30 10:59:34 proc-1      : DEBUG    Added request object to the queue with index 5. There are now 3 items in the queue
# 2009-09-30 10:59:34 proc-1      : INFO     Starting a recv wait
# 2009-09-30 10:59:34 proc-1      : INFO     Removing finished request
# 2009-09-30 10:59:34 proc-1      : INFO     Removing finished request

#################### 0 sec padding
 #2009-09-30 11:05:44 proc-1      : DEBUG    Added request object to the queue with index 43. There are now 2 items in the queue
 #2009-09-30 11:05:44 proc-1      : INFO     Starting a recv wait
 #2009-09-30 11:05:44 proc-1      : INFO     Updating status in request from finished to ready
 #2009-09-30 11:05:44 proc-1      : ERROR    WELEASE WODERICK release unlocked lock
 #==> /tmp/mpi.local.rank0.log <==
 #2009-09-30 11:05:45 proc-0      : INFO     Removing finished request
 #2009-09-30 11:05:45 proc-0      : INFO     Removing finished request

#################### 0 sec padding
#2009-09-30 11:07:27 proc-0      : DEBUG    Network callback in request called
#2009-09-30 11:07:27 proc-0      : INFO     Updating status in request from finished to ready
#2009-09-30 11:07:27 proc-0      : ERROR    WELEASE WODERICK release unlocked lock
#
#==> /tmp/mpi.local.rank1.log <==
#...
#2009-09-30 11:07:27 proc-1      : DEBUG    Request object created for communicator MPI_COMM_WORLD, tag 1 and request_type recv and participant 0
#2009-09-30 11:07:27 proc-1      : DEBUG    Starting a recv network job with tag 1 and 1 callbacks
#2009-09-30 11:07:27 proc-1      : DEBUG    Adding request object to the request queue
#2009-09-30 11:07:27 proc-1      : DEBUG    Added request object to the queue with index 7. There are now 3 items in the queue
#2009-09-30 11:07:27 proc-1      : INFO     Starting a recv wait
#2009-09-30 11:07:28 proc-1      : INFO     Removing finished request
#2009-09-30 11:07:28 proc-1      : INFO     Removing finished request


#################### 1 sec padding
#2009-09-30 11:37:44 proc-1      : DEBUG    Network callback in request called
#2009-09-30 11:37:44 proc-1      : INFO     Updating status in request from finished to ready
#2009-09-30 11:37:44 proc-1      : ERROR    WELEASE WODERICK release unlocked lock
#
#==> /tmp/mpi.local.rank0.log <==
#2009-09-30 11:37:45 proc-0      : DEBUG    Request object created for communicator MPI_COMM_WORLD, tag 1 and request_type recv and participant 1
#2009-09-30 11:37:45 proc-0      : DEBUG    Starting a recv network job with tag 1 and 1 callbacks
#2009-09-30 11:37:45 proc-0      : DEBUG    Adding request object to the request queue
#2009-09-30 11:37:45 proc-0      : DEBUG    Added request object to the queue with index 302. There are now 1 items in the queue
#2009-09-30 11:37:45 proc-0      : INFO     Starting a recv wait






#2009-09-30 13:31:59 proc-1      : INFO     Removing finished request
#Exception in thread Thread-1:
#Traceback (most recent call last):
#  File "/home/fred/python/2.6/lib/python2.6/threading.py", line 525, in __bootstrap_inner
#    self.run()
#  File "/home/fred/Diku/ppmpi/code/pupympi/mpi/__init__.py", line 141, in run
#    comm.update()
#  File "/home/fred/Diku/ppmpi/code/pupympi/mpi/communicator.py", line 129, in update
#    self.request_remove( request )
#  File "/home/fred/Diku/ppmpi/code/pupympi/mpi/communicator.py", line 145, in request_remove
#    del self.request_queue[request_obj.queue_idx]
#KeyError: 194
#
#2009-09-30 13:31:59 proc-1      : DEBUG    Starting a recv network job with tag 1 and 1 callbacks



import time
from mpi import MPI

mpi = MPI()
data = 50*"a"
f = open("/tmp/rank%s.log" % mpi.MPI_COMM_WORLD.rank(), "w")
#mpi.MPI_COMM_WORLD.barrier()
iterations = 0
maxIterations = 250

t1 = mpi.MPI_COMM_WORLD.Wtime()    
if mpi.MPI_COMM_WORLD.rank() is 0:
    for iterations in xrange(maxIterations):
        mpi.MPI_COMM_WORLD.send(1, data+str(iterations), 1)
        #time.sleep(1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        recv = mpi.MPI_COMM_WORLD.recv(1, 1)
        # FIXME Verify data if enabled
        f.write( "Iteration %s completed for rank %s (%s)\n" % (iterations, mpi.MPI_COMM_WORLD.rank(), recv))
        f.flush()
    f.write( "Done for rank 0\n")
elif mpi.MPI_COMM_WORLD.rank() is 1: 
    for iterations in xrange(maxIterations):
        recv = mpi.MPI_COMM_WORLD.recv(0, 1)
        #time.sleep(1)
        mpi.MPI_COMM_WORLD.send(0, data, 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        # FIXME Verify data if enabled
        f.write( "Iteration %s completed for rank %s (%s)\n" % (iterations, mpi.MPI_COMM_WORLD.rank(), recv))
        f.flush()
    f.write( "Done for rank 1\n")
else: 
    raise Exception("Broken state")


t2 = mpi.MPI_COMM_WORLD.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n" % (time, len(data)))
f.flush()
f.close()
mpi.finalize()

