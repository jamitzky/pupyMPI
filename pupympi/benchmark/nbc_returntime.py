from mpi.benchmark import Benchmark
from mpi import MPI

def main(reps):
    mpi   = MPI()
    world = mpi.MPI_COMM_WORLD
    rank  = world.rank()
    size  = world.size()
    handle_list = []
    obj = None          # Will be replaced when calling a NBC.

    if rank == 0:
        print "Benchmarking with %d reps" % reps

    data = range(1000)
    b = Benchmark(communicator=world, roots=range(size))

    # Testing allgather
    bw, _ = b.get_tester("allgather", datasize=rank)
    for _ in range(reps):
        with bw:
            obj = world.iallgather(data)
        handle_list.append(obj)
    world.waitall(handle_list)
    b.flush()


    # Testing barrier

    # Testing bcast

    # Allreduce

    # Alltoall

    # Gather

    # Reduce

    # Scan # UHH.. DOES IT WORK

    mpi.finalize()


    # Post process the files left in user_logs to make it a bit more readable. or implement another script
    # for this.

if __name__ == "__main__":
    try:
        reps = int(sys.argv[1])
    except:
        reps = 10


    main(reps)
