#!/usr/bin/env python2.6
import sys, os
from optparse import OptionParser, OptionGroup
import select, time

import processloaders 
from processloaders import wait_for_shutdown 
from mpi.logger import Logger
from mpi.network.utils import get_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.lib.hostfile import parse_hostfile, map_hostfile
import threading

from mpi.network.utils import pickle

def parse_options():
    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="Pupympi version 0.2 (dev)")
    parser.add_option('-c', '--np', dest='np', type='int', help='The number of processes to start.')
    parser.add_option('--host-file', dest='hostfile', help='Path to the host file defining all the available machines the processes should be started on. If not given, all processes will be started on localhost')

    # Add a logging and debugging
    parser_debug_group = OptionGroup(parser, "Logging and debugging", 
            "Use these settings to control the level of output to the program. The --debug and --quiet options can't be used at the same time. Trying to will result in an error.")
    parser_debug_group.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to %default.')
    parser_debug_group.add_option('-d', '--debug', dest='debug', action='store_true', help='Give you a lot of input')
    parser_debug_group.add_option('-q', '--quiet', dest='quiet', action='store_true', help='Give you no input')
    parser_debug_group.add_option('-l', '--log-file', dest='logfile', default="mpi", help='Which logfile the system should log to. Defaults to %default(.log)')
    parser.add_option_group( parser_debug_group )

    parser_adv_group = OptionGroup(parser, "Advanced options", 
            "Be careful. You could do strange things here.")
    parser_adv_group.add_option('--remote-python', dest='remote_python', default="`which python2.6`", help='Path to Python 2.6 on remote hosts. Defaults to  %default')
    parser_adv_group.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh, rsh (not supported) and popen (local only). Defaults to %default')
    parser_adv_group.add_option('--single-communication-thread', dest='single_communication_thread', action='store_true', help="Use this if you don't want MPI to start two different threads for communication handling. This will limit the number of threads to 3 instead of 4.")
    parser_adv_group.add_option('--disable-full-network-startup', dest='disable_full_network_startup', action='store_true', help="Do not initialize a socket connection between all pairs of processes. If not a second change socket pool algorithm will be used. See also --socket-pool-size")
    parser_adv_group.add_option('--socket-pool-size', dest='socket_pool_size', type='int', default=10, help="Sets the size of the socket pool. Only used it you supply --disable-full-network-startup. Defaults to %default")
    parser_adv_group.add_option('--process-io', dest='process_io', default="direct", help='How to forward I/O (stdout, stderr) from remote process. Options are: none, direct, asyncdirect, localfile or remotefile. Defaults to %default')
    parser_adv_group.add_option('--hostmap-schedule-method', dest='hostmap_schedule_method', default='rr', help="How to distribute the started processes on the available hosts. Options are: rr (round-robin). Defaults to %default")
    parser.add_option_group( parser_adv_group )

    options, args = parser.parse_args()

    if options.debug and options.quiet:
        parser.error("options --debug and -quiet are mutually exclusive")
        
    # if len(args) != 1:
    #     parser.error("There should only be one argument to mpirun. The program to execute ('%s' was parsed)" % args)

    # Trying to find user args
    try:
        user_options = sys.argv[sys.argv.index("--")+1:]
    except ValueError:
        user_options = []

    return options, args, user_options

def io_forwarder(process_list):
    """
    Take a list of processes and relay from their stdout and stderr pipes.
    
    This function continually listens on out and error pipes from all started    
    processes and relays the output to the stdout of the calling process.
    During shutdown a final run through of all the pipes is done to print any
    remaining data.
    """

    pipes = [p.stderr for p in process_list] # Put all stderr pipes in process_list
    pipes.extend( [p.stdout for p in process_list] ) # Put all stdout pipes in process_list
    pipes = filter(None, pipes) # Get rid any pipes that aren't pipes (shouldn't happen but we like safety)

    #logger.debug("Starting the IO forwarder")
    
    # Main loop, select, output, check for shutdown - repeat
    while True:
        
        try:
        # Trying to get stuck processes to accept Ctrl+C and DIE!
            # Any pipes ready with output?
            readlist, _, _ =  select.select(pipes, [], [], 0.5)
            
            # Output anything that we may have found
            for fh in readlist:
                content = fh.readlines()
                for line in content:
                    print >> sys.stdout, line.strip()
            
            # Check if shutdown is in progress    
            if io_shutdown_lock.acquire(False):
                logger.debug("IO forwarder got the lock!.. breaking")
                io_shutdown_lock.release()
                break
            else:
                logger.debug("IO forwarder could not get the lock")
    
            time.sleep(1)
        except KeyboardInterrupt:
            logger.debug("IO forwarder was manually interrupted")
            break
        

    # Go through the pipes manually to see if there is anything
    for pipe in pipes:
        while True:
            line = pipe.read()
            if line:
                print line
            else:
                break

    #logger.debug("IO forwarder finished")

if __name__ == "__main__":
    options, args, user_options = parse_options() # Get options from cli
    if args is None or len(args) == 0: # TODO hack-handle no options
        print "Please use --help for help with options"
        sys.exit()
    executeable = args[0]

    # Start the logger
    logger = Logger(options.logfile, "mpirun", options.debug, options.verbosity, options.quiet)

    # Parse the hostfile.
    try:
        hosts = parse_hostfile(options.hostfile)
    except IOError,ex:
        logger.error("Something bad happended when we tried to read the hostfile: ",ex)
        sys.exit()
    
    # Map processes/ranks to hosts/CPUs
    mappedHosts = map_hostfile(hosts, options.np, options.hostmap_schedule_method) 
    
    s, mpi_run_hostname, mpi_run_port = get_socket() # Find an available socket
    s.listen(5)

    # Whatever is specified at cli is chosen as remote start function (popen or ssh for now)
    remote_start = getattr(processloaders, options.startup_method)

    # List of process objects (instances of subprocess.Popen class)
    process_list = []

    # Start a process for each rank on the host 
    for (host, rank, port) in mappedHosts:
        # Make sure we have a full path
        if not executeable.startswith("/"):
            executeable = os.path.join( os.getcwd(), executeable)
        
        # Mimic our cli call structure also for remotely started processes
        run_options = [options.remote_python, "-u", executeable, "--mpirun-conn-host=%s" % mpi_run_hostname,
                "--mpirun-conn-port=%d" % mpi_run_port, 
                "--rank=%d" % rank, 
                "--size=%d" % options.np, 
                "--socket-pool-size=%d" % options.socket_pool_size, 
                "--verbosity=%d" % options.verbosity, "--process-io=%s" % options.process_io] 

        if options.disable_full_network_startup:
            run_options.append('--disable-full-network-startup')

        # Special options
        # TODO: This could be done nicer, no need for spec ops
        if options.quiet:
            run_options.append('--quiet')
        if options.debug:
            run_options.append('--debug')
        run_options.append('--log-file=%s' % options.logfile)

        # Adding user options. GNU style says this must be after the --
        run_options.append( "--" )
        run_options.extend( user_options )
        
        # Now start the process and keep track of it
        p = remote_start(host, run_options, options.process_io, rank)
        process_list.append(p)
            
        #logger.debug("Process with rank %d started" % rank)

    # NOTE: Why is this not started before the remote processes?
    # Start a thread to handle io forwarding from processes
    if options.process_io == "asyncdirect":
        io_shutdown_lock = threading.Lock() # lock used to signal shutdown
        io_shutdown_lock.acquire() # make sure no one thinks we are shutting down yet
        t = threading.Thread(target=io_forwarder, args=(process_list,))
        t.start()
        
    # Listing of (rank, host, port) for all the processes
    all_procs = []
    # Listing of socket connections to all the processes
    sender_conns = []

    #logger.debug("Waiting for %d processes" % options.np)
    
    # Recieve listings from newly started proccesses phoning in
    # TODO: This initial communication should be more robust
    # - if procs die before contacting mother, we hang
    # - if procs don't send complete info in first attempt we go haywire
    # - if mother is contacted on port from anyone but the proper processes we could hang or miss a process
    for i in range(options.np):       
        sender_conn, sender_addr = s.accept()
        sender_conns.append( sender_conn )
        
        # Receiving data about the communicator, by unpacking the head etc.
        rank, data = get_raw_message(sender_conn)
        data = pickle.loads(data)
        (communicator, sender, tag, message) = data
        
        all_procs.append( message ) # add (rank,host,port) for process to the listing
    #logger.debug("Received information for all %d processes" % options.np)
    
    # Send all the data to all the connections, closing each connection afterwards
    # TODO: This initial communication should also be more robust
    # - if a proc does not recieve proper info all bets are off
    # - if a proc is not there to recieve we hang (at what timeout?)
    data = (-1, -1, constants.TAG_INITIALIZING, all_procs)
    message = prepare_message(data, -1)
    for conn in sender_conns:
        conn.send(message)
        conn.close()
    # Close own "server" socket
    s.close()
    
    # Wait for all started processes to die
    exit_codes = wait_for_shutdown(process_list)    
    # Check exit codes from started processes
    any_failures = sum(exit_codes) is not 0
    if any_failures:
        logger.error("Some processes failed to execute, exit codes in order: %s" % exit_codes)
        
    if options.process_io == "pipe":        
        # Signal shutdown to io_forwarder thread
        io_shutdown_lock.release()    
        # Wait for the IO_forwarder thread to stop
        t.join()
        #logger.debug("IO forward thread joined")
        
    sys.exit(1 if any_failures else 0)
