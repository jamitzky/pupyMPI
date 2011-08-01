from mpi.benchmark import Benchmark
from mpi import MPI
from mpi.collective.operations import MPI_sum

def main(reps):
    mpi   = MPI()
    world = mpi.MPI_COMM_WORLD
    rank  = world.rank()
    size  = world.size()
    handle_list = []
    obj = None          # Will be replaced when calling a NBC.

    if rank == 0:
        print "Benchmarking with %d reps" % reps

    datacount = 1000
    while datacount % size != 0:
        datacount += 1

    data = range(datacount)
    b = Benchmark(communicator=world, roots=range(size))

    # Testing allgather
    bw, _ = b.get_tester("allgather", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.iallgather(data)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Testing barrier
    bw, _ = b.get_tester("barrier", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.ibarrier()
        handle_list.append(obj)
    world.waitall(handle_list)

    # Testing bcast
    bw, _ = b.get_tester("bcast", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.ibcast(data, root=0)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Allreduce
    bw, _ = b.get_tester("allreduce", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.iallreduce(data, MPI_sum)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Alltoall
    bw, _ = b.get_tester("alltoall", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.ialltoall(data)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Gather
    bw, _ = b.get_tester("gather", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.igather(data)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Reduce
    bw, _ = b.get_tester("reduce", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.ireduce(data, MPI_sum, root=0)
        handle_list.append(obj)
    world.waitall(handle_list)

    # Scan # UHH.. DOES IT WORK
    bw, _ = b.get_tester("scan", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.iscan(data, MPI_sum)
        handle_list.append(obj)
    world.waitall(handle_list)

    b.flush()
    mpi.finalize()


    # Post process the files left in user_logs to make it a bit more readable. or implement another script
    # for this.

if __name__ == "__main__":
    try:
        reps = int(sys.argv[1])
    except:
        reps = 10


    main(reps)
