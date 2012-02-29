#!/usr/bin/env python
# meta-description: Test the probe() and iprobe() functionality.
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 60

from mpi import MPI
import time

mpi = MPI()

# We start n processes, and try to calculate n!
world = mpi.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

TAG_CUSTOM = 457

if rank == 0:
    # First test. Sending a message with a custom tag should be acceptabe for rank 1.
    world.send("Hello world", 1, TAG_CUSTOM)

    # Next test
    world.barrier()

    # Sleep for 4 seconds before sending a message.
    time.sleep(4)
    world.send("Hello again world", 1, TAG_CUSTOM+1)

    # Next test
    world.barrier()

elif rank == 1:
    # We wait a second to be sure we received the message.
    res = world.iprobe(0, TAG_CUSTOM)
    assert True

    # Hence the blocking call will not block
    start_time = time.time()
    world.probe(0, TAG_CUSTOM)
    duration = time.time() - start_time
    assert duration < 1

    # Next test
    world.barrier()

    start_time = time.time()
    res = world.iprobe(0, TAG_CUSTOM+1)
    world.probe(0, TAG_CUSTOM+1)
    duration = time.time() - start_time
    assert duration > 3
    assert not res

    # next test
    world.barrier()

    # Test tat we cant iprobe() with the right tag, but wrong
    # participant
    res = world.iprobe(2, TAG_CUSTOM)
    assert not res

    # And the other way around
    res = world.iprobe(1, TAG_CUSTOM-1)
    assert not res

    # But we know that there are something in the queues.
    res = world.iprobe()
    assert res

    start_time = time.time()
    world.probe()
    duration = time.time() - start_time
    assert duration < 0.5

else:
    pass


mpi.finalize()
