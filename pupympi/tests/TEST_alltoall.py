from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.rank()

send_data = ["%d --> %d" % (rank, x) for x in range(size)]

recv_data = mpi.alltoall(send_data)

expected_data = [ '%d --> %d' % (x, rank) for x in range(size)]

assert sorted(recv_data) == sorted(expected_data)
