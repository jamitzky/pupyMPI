#!/usr/bin/env python2.6
# This is the main pupympi startup script. See the usage function
# for information about it
"""
mpirun.py (pupympi) 

Usage: ./mpirun.py [OPTION]... [PROGRAM]...
Start the program with pupympi

    -c | --np <arg0>            The number of processes to run
    -d | --debug                Makes the system prints a bunch
                                of debugging information. You can
                                control the verbosity of the output
                                with the -v parameter.
    -v | --verbosity <arg0>     The level of verbosity the system 
                                should print. Set this between 0 (no output)
                                and 3 (a lot of input).
    -q | --quiet                Overriddes any argument set by -v and makes
                                sure the framework is quiet. 
    -l | --log-file <arg0>      Sets which log file the system should insert
                                debug information into.
    -f | --host-file <arg0>    The host file where the processes should be
                                started. See the documentation for the proper
                                format. 
    -h | --help                 Display this help. 

""" 

#import mpi, sys, os
#limiting import since mpi cannot be found currently
import sys, os, socket
from mpi.processloaders import popen as remote_start
from mpi.processloaders import shutdown, gather_io 
from mpi.logger import Logger

try:
    import cPickle as pickle
except ImportError:
    import pickle

def usage():
    print __doc__
    sys.exit()

def parse_hostfile(hostfile):
    # Parses hostfile, and returns list of tuples of the form (hostname, hostparameters_in_dict)
    # NOTE: Standard port below and maybe other defaults should not be hardcoded here
    # (defaults should probably be a parameter for this function)
    logger = Logger()

    defaults = {"cpu":1,"max_cpu":1024,"port":14000}
    malformed = False # Flag bad hostfile
    hosts = []
    
    if not hostfile:
        logger.info("No hostfile specified - going with lousy defaults!")
        # If no hostfile is specified, default is localhost with default parameters
        hosts = [("localhost",defaults)]
    else:
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
                        #NOTE: Should check for value type here (probably non-int = malformed for now)
                
                hosts += [(hostname, specified)]

        fh.close()

    if len(hosts):
        # uncomment below if you wanna see the format
        #for (hName, hDict) in hosts:
        #   print hName
        #   print hDict
        return hosts
    else:
        raise IOError("No lines in your hostfile, or something else went wrong")
            
def map_hostfile(hosts, np=1, type="rr", overmapping=True):
    # Assign ranks and host to all processes
    # NOTE: We only do primitive overcommitting so far.
    # Eventually we should decide how to best map more processes than "cpu" specifies, onto hosts
    # eg. does higher cpu/max_cpu ratio mean a more realistic estimate of a good max cpu?

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
            logger.info("gonna overmap")
        else: # Overmapping needed but not allowed
            logger.info("Number of processes exceeds the total CPUs and overmapping is not allowed")
            return []
    else: # Can't be done even with overmapping
        logger.info("Number of processes exceeds the maximum allowed CPUs")
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
            #DEBUG
            #print "mapped %i to %s" % (rank,hostname)
            
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
            #DEBUG
            #print "overmapped %i to %s" % (rank,hostname)
            
            if type == "rr": # round-robin?
                i += 1 # for round-robin always go to next host
            
        else: # if no CPUs left we always go to next host
            i += 1 # pick next host
            
    #DEBUG
    #print mappedHosts
    return mappedHosts


if __name__ == "__main__":

    import getopt
    try:
        optlist, args = getopt.gnu_getopt(sys.argv[1:], 'c:dv:ql:f:h', ['np=','verbosity=','quiet','log-file=','host','host-file=','debug',])
    except getopt.GetoptError, err:
        print str(err)
        usage()

    np = 0
    debug = False
    verbosity = 1
    quiet = False

    logfile = None
    hostfile = None
    
    if not optlist:
        usage()

    for opt, arg in optlist:
        if opt in ("-h", "--help"):
            usage()
        
        if opt in ("-c","--np"):
            try:
                np = int(arg)
            except ValueError:
                print "Argument to %s should be an integer" % opt
                usage()

        if opt in ("-d", "--debug"):
            debug = True

        if opt in ("-v", "--verbosity"):
            verbosity = int(arg)

        if opt in ("-q", "--quiet"):
            quiet = True

        if opt in ("-l", "--log-file"):
            logfile = arg
            
        if opt in ("-f", "--host-file"):
            hostfile = arg
        else:
            # NOTE: Rune mumbled that it should not be None here, but it does the job for now
            hostfile = None # No hostfile specified, go with default

    # Start the logger
    logger = Logger(logfile or "mpi", "mpirun", debug, verbosity, quiet)

    # Parse the hostfile.
    try:
        hosts = parse_hostfile(hostfile)
    except IOError:
        logger.error("Something bad happended when we tried to read the hostfile. ")
        sys.exit()
    
    # Map processes/ranks to hosts/CPUs
    mappedHosts = map_hostfile(hosts, np,"rr") # NOTE: This call should get scheduling option from args to replace "rr" parameter

    # We hardcode for TCP currently. This should be made more generic in the future. 
    mpi_run_hostname = socket.gethostname()
    logger.debug("Found hostname: %s" % mpi_run_hostname)
    
    # FIXME: Fix what?
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    for tries in range(10):
        mpi_run_port = 5555+tries # Rewrite to find some port
        try:
            s.bind((mpi_run_hostname, mpi_run_port))
            break
        except socket.error:
            continue
            
    s.listen(5)
    logger.debug("Socket bound to port %d" % mpi_run_port)
    
    # Start a process for each rank on associated host. 
    for (host, rank, port) in mappedHosts:
        port = port+rank
        # Prepare the command line args for the subprocesses

        # This should be rewritten to be nicer
        executeable = sys.argv[-1]
        # Make sure we have a full path
        if not executeable.startswith("/"):
            executeable = os.path.join( os.getcwd(), sys.argv[-1])
        
        arguments = ["python", "-u", executeable, "--mpirun-conn-host=%s" % mpi_run_hostname,"--mpirun-conn-port=%d" % mpi_run_port, "--rank=%d" % rank, "--size=%d" % np, "--verbosity=%d" % verbosity] 
        
        if quiet:
            arguments.append('--quiet')

        if debug:
            arguments.append('--debug')

        if logfile:
            arguments.append('--log-file=%s' % logfile)
            
        remote_start(host, arguments)
            
        logger.debug("Process with rank %d started" % rank)
        
    # Listing for (rank, host, port) from all the procs.
    all_procs = []
    sender_conns = []
    for _ in mappedHosts:
        sender_conn, sender_addr = s.accept()
        sender_conns.append( sender_conn )
        # Recieve listings from newly started proccesses phoning in
        data = pickle.loads(sender_conn.recv(4096))
        all_procs.append( data )
        logger.debug("Received initial startup date from proc-%d" % data[2])
    
        
    # Send all the data to all the connections
    for conn in sender_conns:
        conn.send( pickle.dumps( all_procs ))
    
    # Close all the connections
    [ c.close for c in sender_conns ]

    s.close()
    # debug: check status on all children
    gather_io()

    shutdown()
    # debug: check status on all children
    # import time
    # time.sleep(2)
    #remote_gather(logger)
    sys.exit(0)
