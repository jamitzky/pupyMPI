#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
from mpi.logger import Logger

def parse_hostfile(hostfile):
    """
    Parses hostfile, and returns list of tuples of the form (hostname, hostparameters_in_dict)

    NOTE: Defaults are hard-coded here. Nicer solution would be... nice
    """
    logger = Logger()

    defaults = {"cpu":1,"max_cpu":1024,"port":14000}
    malformed = False # Flag bad hostfile
    hosts = []
    
    try:
        fh = open(hostfile, "r")
        for line in fh.readlines():
            pseudo_list = line.split( "#", 1 )            
            content = pseudo_list[0] # the comment would be pseudo_list[1] but those are ignored
            if content <> '\n' and content <> '': # Ignore empty lines and lines that are all comment
                values = content.split() # split on whitespace with multiple spaces ignored
                # There is always a hostname
                hostname = values[0]
                specified = defaults.copy()
                                
                # Check if non-defaults were specified
                values = values[1:] # Ignore hostname we already know that
                for v in values:
                    (key,separator,val) = v.partition('=')
                    if separator == '': # empty if malformed key-value pair
                        malformed = True
                    elif not defaults.has_key(key): # unrecognized keys are considered malformed
                        malformed = True
                    else:                        
                        specified[key] = int(val)
                
                hosts += [(hostname, specified)]

        fh.close()
    except:
        logger.info("No hostfile specified or hostfile invalid - all processes will run on default machines (typically localhost)")
        hosts = [("localhost",defaults)]
    
    # Fall back to defaults if user messed up the hostfile    
    if malformed:
        hosts = [("localhost",defaults)]
    else:
        return hosts
            

def map_hostfile(hosts, np=1, type="rr", overmapping=True):
    """
    Assign ranks and host to all processes

    NOTE: We only do primitive overcommitting so far.
    In the future we should decide how to best map more processes than "cpu" specifies, onto hosts
    eg. does higher cpu/max_cpu ratio mean a more realistic estimate of a good max cpu?
    """
    logger = Logger()

    mappedHosts = [] # list containing the (host,rank) tuples to return   
    hostCount = len(hosts) # How many hosts do we have
        
    # Check viability of mapping np onto all CPUs from all hosts
    actualCPUs = 0 # Real physical CPUs
    maxCPUs = 0 # Allowed overmapped CPUs
    for (hostname,params) in hosts:
        actualCPUs += params["cpu"]
        maxCPUs += params["max_cpu"]

    # Check if it can be done with or without overmapping
    if actualCPUs >= np:  # No need to overmap
        pass
    elif maxCPUs >= np: # Overmapping is needed
        if overmapping: # Overmapping allowed?
            logger.warning("Insufficient hosts - overmapping processes.")
        else: # Overmapping needed but not allowed
            logger.error("Number of processes exceeds the total CPUs and overmapping is not allowed")
            return []
    else: # Can't be done even with overmapping
        logger.error("Number of processes exceeds the maximum allowed CPUs")
        return []
        
    i = 0 # host indexer
    rank = 0 # rank counter
    mapType = "cpu" # Start by mapping only on actual CPUs (non-overmapping)
    
    while rank < actualCPUs and rank < np: # Assign to actual CPUs until no more CPUs (or all ranks assigned if not overmapping)
        (hostname,params) = hosts[i%hostCount]
        if params[mapType] > 0: # Are there CPUs available on host?
            params[mapType] -= 1 # mark as one less unused
            params["max_cpu"] -= 1 # max cpu includes actual ones so decrease here too
            mappedHosts += [(hostname, rank, params["port"])] # map it
            rank += 1 # assign next rank
            
            if type == "rr": # round-robin?
                i += 1 # for round-robin always go to next host
            
        else: # if no CPUs left we always go to next host
            i += 1 # pick next host

    # The overmapping is done in it's own loop since we might wanna do things a bit
    #differently here.
    mapType = "max_cpu"
    while rank < np: # Overmap any remaining ranks until all needed ranks are mapped
        (hostname,params) = hosts[i%hostCount]
        if params[mapType] > 0: # Are there CPUs available on host?
            params[mapType] -= 1 # mark as one less unused
            mappedHosts += [(hostname, rank, params["port"])] # map it
            rank += 1 # assign next rank
            
            if type == "rr": # round-robin?
                i += 1 # for round-robin always go to next host
            
        else: # if no CPUs left we always go to next host
            i += 1 # pick next host
            
    return mappedHosts
