from mpi.logger import Logger

class HostfileMapException(Exception): pass

def generate_localhost_data(hosts, np):
    if not hosts:
        Logger().warning("No hostfile. Overmapping on localhost. Unless you are developing right now, this might not be what you want.")
        return [("localhost", i) for i in range(np)]

def round_robin(hosts, total_cpu, max_cpu, np=1, overmapping=True):
    l = generate_localhost_data(hosts, np)
    if l: return l

    if np > total_cpu:
        # Overmapping.
        if not overmapping or np > max_cpu:
            raise HostfileMapException("Number of processes exceeds the maximum allowed CPUs")

        Logger().warning("Not enough hosts. Overmapping in effect. ")

    mapped_hosts = []
    host_count = {}
    rank = 0
    done = False

    while not done:
        for host in hosts:
            hostname = host['host']

            if hostname not in host_count:
                host_count[hostname] = 0

            # Just check that this host allows more virtual CPUs on it
            if host_count[hostname] < host['max_cpu']:
                host_count[hostname] += 1
            else:
                continue

            mapped_hosts.append( (hostname, rank) )
            rank += 1

            if rank == np:
                done = True
                break

    return mapped_hosts

def greedy_fit(hosts, total_cpu, max_cpu, np=1, overmapping=True):
    # There is no weight here, so we simply divide.
    l = generate_localhost_data(hosts, np)
    if l: return l
    mapped_hosts = []

    per_host = np / len(hosts)
    rank = 0
    for host in hosts:
        hostname = host['host']
        for _ in range(per_host):
            mapped_hosts.append( (hostname, rank))
            rank += 1

    if np != rank:
        missing = np - rank + 1
        print mapped_hosts
        print missing
        for host in hosts[:missing]:
            hostname = host['host']
            mapped_hosts.append( (hostname, rank))
            rank += 1

    return mapped_hosts

def find_mapper(module_or_func):
    mod = __import__("mpi.lib.hostfile.mappers", fromlist="mpi.lib.hostfile")
    mapper = getattr(mod, module_or_func, None)

    if not mapper:
        # Try to import the module.
        if module_or_func.find(".") == -1:
            raise Exception("Cant import a custom hostmapper. Maybe you supplied something in a bad format")

        try:
            split = module_or_func.split(".")
            mod = __import__(split[:-1])
            func = split[-1]
            mapper = getatr(mod, func, None)
        except Exception, e:
            Logger().warn("Cant import the custom module. The exception raised is %s" % e)

    if mapper and callable(mapper):
        return mapper

