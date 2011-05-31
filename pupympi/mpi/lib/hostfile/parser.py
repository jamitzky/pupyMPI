import ConfigParser
import copy
from mpi.logger import Logger

def parse_hostfile(filepath="hostfile", limit_to=None):
    config = ConfigParser.SafeConfigParser()
    config.read(filepath)
    
    # The returned data will be at tuple containing
    # the hosts, sum of cpus and sum of allowed overmapped cpus
    sum_cpu = 0
    sum_maxcpu = 0
    hosts = []

    # As a default, we use all the sections defining
    # hosts. If - on the other hand - the user defined
    # a section called [ActiveNodes], only the secions
    # mention there will be read.
    sections = config.sections()

    # Filter the sections by looking in the ActiveNodes,
    # so only a subset of the section will be used.
    if "ActiveNodes" in sections:
        sections.remove("ActiveNodes")
        try:
            active_sections = config.get("ActiveNodes", "active")
            active_sections = [s.strip() for s in active_sections.split(",")]
        
            # Test if there is global overlap
            if not all([s in sections for s in active_sections]):
                raise Exception("There were sections defined in the ActiveNodes that does not exist")
            
            sections = active_sections
        except ConfigParser.NoOptionError:
            pass
        
    if limit_to:
        for s in sections:
            if s not in limit_to:
                sections.remove(s)
        
    defaults = {'cpu' : 0, 'max_cpu' : 0}
    if "Defaults" in config.sections():
        # Fetch the default keys. 
        for key in defaults:
            defaults[key] = config.getint("Defaults", key)
                  
    # We are now ready to parse the remaining sections
    for section in sections:
        try:
            nodes = config.get(section, "nodes").split(",")
        except ConfigParser.NoOptionError:
            Logger().warning("Found section %s in hostfile, but it does not include any nodes. This section will not contribture anything to the later process to host mapping.")
        for node in nodes:
            node = node.strip()
            
            # Use the defaults as defaults (wauw). Override them after.
            s = copy.copy(defaults)
            s["host"] = node    
            for key in defaults:
                try:
                    s[key] = config.getint(section, key)
                except ConfigParser.NoOptionError:
                    pass
                
            # Aggregate some key information
            sum_maxcpu += s["max_cpu"]
            sum_cpu += s["cpu"]
                
            hosts.append(s)
            
    if sum_cpu > sum_maxcpu:
        Logger().warn("Hostfile parser detected that the hostfile specifies more actual CPUs than 'virtual")
        
    return hosts, sum_cpu, sum_maxcpu

