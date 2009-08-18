#!/usr/bin/env python2.6
import sys, os, socket
from optparse import OptionParser, OptionGroup

from mpi import processloaders 
from mpi.processloaders import shutdown, gather_io 
from mpi.logger import Logger
from mpi.tcp import get_socket

try:
    import cPickle as pickle
except ImportError:
    import pickle

def parse_hostfile(hostfile): # {{{1
    """
    Parses hostfile, and returns list of tuples of the form (hostname, hostparameters_in_dict)
    NOTE: Standard port below and maybe other defaults should not be hardcoded here
    (defaults should probably be a parameter for this function)
    """
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

def map_hostfile(hosts, np=1, type="rr", overmapping=True): # {{{1
    """
    Assign ranks and host to all processes
    NOTE: We only do primitive overcommitting so far.
    Eventually we should decide how to best map more processes than "cpu" specifies, onto hosts
    eg. does higher cpu/max_cpu ratio mean a more realistic estimate of a good max cpu?
    """


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
            
            if type == "rr": # round-robin?
                i += 1 # for round-robin always go to next host
            
        else: # if no CPUs left we always go to next host
            i += 1 # pick next host
            
    return mappedHosts

def parse_options():

    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="Pupympi version 0.01 (dev)")
    parser.add_option('-c', '--np', dest='np', type='int', help='The number of processes to start.')
    parser.add_option('--host-file', dest='hostfile', help='Path to the host file defining all the available machines the processes should be started on. If not given, all processes will be started on localhost')

    # Add a logging and debugging
    parser_debug_group = OptionGroup(parser, "Logging and debugging", 
            "Use these settings to control the level of output to the program. The --debug and --quiet options can't be used at the same time. Trying to will result in an error.")
    parser_debug_group.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to 1.')
    parser_debug_group.add_option('-d', '--debug', dest='debug', action='store_true', help='Give you a lot of input')
    parser_debug_group.add_option('-q', '--quiet', dest='quiet', action='store_true', help='Give you no input')
    parser_debug_group.add_option('-l', '--log-file', dest='logfile', default="mpi", help='Which logfile the system shoud log to. Defaults to mpi(.log)')
    parser.add_option_group( parser_debug_group )

    parser_adv_group = OptionGroup(parser, "Advanced options", 
            "Be carefull. You could actually to strange things here. OMG Ponies!")
    parser_adv_group.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh and popen. Defaults to ssh')
    parser.add_option_group( parser_adv_group )

    options, args = parser.parse_args()

    if options.debug and options.quiet:
        parser.error("options --debug and -quiet are mutually exclusive")

    # Trying to find user args
    import sys
    try:
        user_options = sys.argv[sys.argv.index("--")+1:]
    except ValueError:
        user_options = []

    return options, args, user_options

if __name__ == "__main__":
    options, args, user_options = parse_options()
    executeable = args[0]

    # Start the logger
    logger = Logger(options.logfile, "mpirun", options.debug, options.verbosity, options.quiet)

    # Parse the hostfile.
    try:
        hosts = parse_hostfile(options.hostfile)
    except IOError:
        logger.error("Something bad happended when we tried to read the hostfile. ")
        sys.exit()
    
    # Map processes/ranks to hosts/CPUs
    mappedHosts = map_hostfile(hosts, options.np,"rr") # NOTE: This call should get scheduling option from args to replace "rr" parameter

    s, mpi_run_hostname, mpi_run_port = get_socket()
            
    s.listen(5)
    logger.debug("Socket bound to port %d" % mpi_run_port)

    remote_start = getattr(processloaders, options.startup_method)

    # Start a process for each rank on associated host. 
    for (host, rank, port) in mappedHosts:
        port = port+rank

        # Make sure we have a full path
        if not executeable.startswith("/"):
            executeable = os.path.join( os.getcwd(), executeable)
        
        run_options = ["python2.6", "-u", executeable, "--mpirun-conn-host=%s" % mpi_run_hostname,
                "--mpirun-conn-port=%d" % mpi_run_port, 
                "--rank=%d" % rank, 
                "--size=%d" % options.np, 
                "--verbosity=%d" % options.verbosity] 
        
        if options.quiet:
            run_options.append('--quiet')

        if options.debug:
            run_options.append('--debug')

        run_options.append('--log-file=%s' % options.logfile)

        # Adding user options. Gnu style says this must be after --
        run_options.append( "--" )
        run_options.extend( user_options )

        remote_start(host, run_options)
            
        logger.debug("Process with rank %d started" % rank)
        
    # Listing for (rank, host, port) from all the procs.
    all_procs = []
    sender_conns = []

    logger.debug("Waiting for %d processes" % options.np)

    for i in range(options.np):
        sender_conn, sender_addr = s.accept()
        sender_conns.append( sender_conn )
        # Recieve listings from newly started proccesses phoning in
        data = pickle.loads(sender_conn.recv(4096))
        all_procs.append( data )
        logger.debug("%d: Received initial startup date from proc-%d" % (i, data[2]))

    logger.debug("Received information for all %d processes" % options.np)
    
    # Send all the data to all the connections
    for conn in sender_conns:
        conn.send( pickle.dumps( all_procs ))
    
    # Close all the connections
    [ c.close for c in sender_conns ]
    # Close own "server" socket
    s.close()
    
    # Check status on all children
    gather_io()

    shutdown()
    # debug: check status on all children
    # import time
    # time.sleep(2)
    #remote_gather(logger)
    sys.exit(0)
