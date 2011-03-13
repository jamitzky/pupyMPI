
class HostfileMapException(Exception): pass

def generate_localhost_data(hosts, np):
    if not hosts:
        return [("localhost", i) for i in range(np)]

def round_robin(hosts, total_cpu, max_cpu, np=1, overmapping=True):
    l = generate_localhost_data(hosts, np)
    if l: return l    
    
    if np > total_cpu:
        # Overmapping.
        if not overmapping or np > max_cpu:
            raise HostfileMapException("Number of processes exceeds the maximum allowed CPUs")
        
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