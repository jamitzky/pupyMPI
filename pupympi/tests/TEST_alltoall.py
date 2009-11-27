from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

send_data = ["%d --> %d" % (rank, x) for x in range(size)]

recv_data = world.alltoall(send_data)

expected_data = [ '%d --> %d' % (x, rank) for x in range(size)]

try:
    assert sorted(recv_data) == sorted(expected_data)
except AssertionError, e:
    print "Got AssertionError. "
    print "\tExcepted: %s" % expected_data
    print "\tReceived data: %s" % recv_data
    raise e

mpi.finalize()