#!/usr/bin/env python2.6
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
import sys, os, copy, signal
from optparse import OptionParser, OptionGroup
import select, time

# Allow the user to import mpi without specifying PYTHONPATH in the environment
mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

import processloaders 
from mpi.logger import Logger
from mpi.network import utils
from mpi.network.utils import create_random_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.lib.hostfile import parse_hostfile, map_hostfile
import threading

from mpi.network.utils import pickle

def parse_options():
    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))
    parser.add_option('-c', '--np', dest='np', type='int', help='The number of processes to start.')
    parser.add_option('--host-file', dest='hostfile', default="hostfile", help='Path to the host file defining all the available machines the processes should be started on. If not given, all processes will be started on localhost')

    # Add logging and debugging options
    parser_debug_group = OptionGroup(parser, "Logging and debugging", 
            "Use these settings to control the level of output to the program. The --debug and --quiet options can't be used at the same time. Trying to will result in an error.")
    parser_debug_group.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to %default.')
    parser_debug_group.add_option('-d', '--debug', dest='debug', action='store_true', help='Give you a lot of input')
    parser_debug_group.add_option('-u', '--unbuffered', dest='buffer', action='store_true', help='Try not to buffer')
    parser_debug_group.add_option('-q', '--quiet', dest='quiet', action='store_true', help='Give you no input')
    parser_debug_group.add_option('-l', '--log-file', dest='logfile', default="mpi", help='Which logfile the system should log to. Defaults to %default(.log)')
    parser.add_option_group( parser_debug_group )

    # Add advanced options
    parser_adv_group = OptionGroup(parser, "Advanced options", 
            "Be careful. You could do strange things here.")
    parser_adv_group.add_option('--remote-python', dest='remote_python', default="`which python2.6`", help='Path to Python 2.6 on remote hosts. Defaults to  %default')
    parser_adv_group.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh, rsh (not supported) and popen (local only). Defaults to %default')
    parser_adv_group.add_option('--single-communication-thread', dest='single_communication_thread', action='store_true', help="Use this if you don't want MPI to start two different threads for communication handling. This will limit the number of threads to 3 instead of 4.")
    parser_adv_group.add_option('--disable-full-network-startup', dest='disable_full_network_startup', action='store_true', help="Do not initialize a socket connection between all pairs of processes. If not a second chance socket pool algorithm will be used. See also --socket-pool-size")
    parser_adv_group.add_option('--socket-pool-size', dest='socket_pool_size', type='int', default=20, help="Sets the size of the socket pool. Only used it you supply --disable-full-network-startup. Defaults to %default")
    parser_adv_group.add_option('--process-io', dest='process_io', default="direct", help='How to forward I/O (stdout, stderr) from remote process. Options are: none, direct, asyncdirect, localfile or remotefile. Defaults to %default')
    parser_adv_group.add_option('--hostmap-schedule-method', dest='hostmap_schedule_method', default='rr', help="How to distribute the started processes on the available hosts. Options are: rr (round-robin). Defaults to %default")
    parser_adv_group.add_option('--enable-profiling', dest='enable_profiling', action='store_true', help="Whether to enable profiling of MPI scripts. Profiling data are stored in ./logs/pupympi.profiling.rank<rank>. Defaults to off.")
    parser_adv_group.add_option('--socket-poll-method', dest='socket_poll_method', default=False, help="Specify which socket polling method to use. Available methods are epoll (Linux only), kqueue (*BSD only), poll (most UNIX variants) and select (all operating systems). Default behaviour is to attempt to use either epoll or kqueue depending on the platform, then fall back to poll and finally select.")
    parser_adv_group.add_option('--yappi', dest='yappi', action='store_true', help="Whether to enable profiling with Yappi. Defaults to off.")
    parser_adv_group.add_option('--yappi-sorttype', dest='yappi_sorttype', help="Sort type to use with yappi. One of: name (function name), ncall (call count), ttotal (total time), tsub (total time minus subcalls), tavg (total average time)")
    parser.add_option_group( parser_adv_group )

    try:
        options, args = parser.parse_args()
        
        if options.debug and options.quiet:
            parser.error("options --debug and -quiet are mutually exclusive")
            
        if args is None or len(args) == 0: 
            parser.error("You need to specify a positional argument: the user program to run.")

        executeable = args[0]

        try:
            user_options = sys.argv[sys.argv.index("--")+1:]
        except ValueError:
            user_options = []

        return options, args, user_options, executeable
    except Exception, e:
        print "It's was not possible to parse the arguments. Error received: %s" % e
        sys.exit(1)
        
global sender_conns

def signal_handler(signal, frame):
    print 'Interrupt signal trapped - attempting to nuke children. You may want to verify manually that nothing is hanging.'
    COMM_ID = -1
    COMM_RANK = -1
    data = (COMM_ID, COMM_RANK, constants.TAG_SHUTDOWN, all_procs)
    message = prepare_message(data, constants.CMD_ABORT)
    for conn in sender_conns:
        utils.robust_send(conn, message)
    processloaders.terminate_children()
    sys.exit(3)

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

    logger.debug("Starting the IO forwarder")
    
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
            if io_shutdown_event.is_set():
                logger.debug("IO forwarder got the signal !.. breaking")
                break
    
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

    logger.debug("IO forwarder finished")

if __name__ == "__main__":
    # Try to get around export pythonpath issue
    
    options, args, user_options, executeable = parse_options() # Get options from cli

    # Set log dir
    logdir = constants.LOGDIR # NOTE: This could be command line option
    if not os.access(logdir, os.W_OK):
        raise Exception("Logging directory not writeable - check that this path exists and is writeable:\n%s" % constants.LOGDIR)
    
    # Start the logger
    logger = Logger(options.logfile, "mpirun", options.debug, options.verbosity, options.quiet)

    # Map processes/ranks to hosts/CPUs
    mappedHosts = map_hostfile(parse_hostfile(options.hostfile), options.np, options.hostmap_schedule_method) 
    
    #logger.debug("Hosts are now configured: " + str(mappedHosts))
    s, mpi_run_hostname, mpi_run_port = create_random_socket() # Find an available socket
    s.listen(5)

    # Whatever is specified at cli is chosen as remote start function (popen or ssh for now)
    remote_start = getattr(processloaders, options.startup_method)

    # List of process objects (instances of subprocess.Popen class)
    process_list = []

    # Make sure we have a full path
    if not executeable.startswith("/"):
        executeable = os.path.join( os.getcwd(), executeable)

    # Mimic our cli call structure also for remotely started processes
    global_run_options = [options.remote_python, "-u", executeable, "--mpirun-conn-host=%s" % mpi_run_hostname,
            "--mpirun-conn-port=%d" % mpi_run_port, 
            "--size=%d" % options.np, 
            "--socket-pool-size=%d" % options.socket_pool_size, 
            "--verbosity=%d" % options.verbosity, 
            "--process-io=%s" % options.process_io,
            "--log-file=%s" % options.logfile,
    ] 
    
    if options.socket_poll_method:
        global_run_options.append('--socket-poll-method=%s' % options.socket_poll_method)
    
    if options.disable_full_network_startup:
        global_run_options.append('--disable-full-network-startup')

    if options.enable_profiling:
        global_run_options.append('--enable-profiling')

    if options.yappi:
        global_run_options.append('--yappi')

    if options.yappi_sorttype:
        global_run_options.append('--yappi-sorttype=%s' % options.yappi_sorttype)

    for flag in ("quiet", "debug"):
        value = getattr(options, flag, None)
        if value:
            global_run_options.append("--"+flag)

    # Start a process for each rank on the host 
    for (host, rank, port) in mappedHosts:
        run_options = copy.copy(global_run_options)
        run_options.append("--rank=%d" % rank) 
        
        # Adding user options. GNU style says this must be after the --
        run_options.append( "--" )
        run_options.extend( user_options )
        
        # Now start the process and keep track of it
        p = remote_start(host, run_options, options.process_io, rank)
        process_list.append(p)
            
        #logger.debug("Process with rank %d started" % rank)


    """
    NOTE: Now we have a proccess list and can start the io forwarder if needed
    At this point processes are of course already running meaning we could
    theoretically miss a bit of the first output. The solution is a bit bothersome
    since we would need to delay actually starting the remotely created processes
    and it does not matter a whole lot since they all have to phone in to mother
    before really doing anything.
    """
    # Start a thread to handle io forwarding from processes
    if options.process_io == "asyncdirect":
        # Declare an event for proper shutdown. When the system is ready to
        # shutdown we signal the event. People looking at the signal will catch
        # it and shutdown.
        io_shutdown_event = threading.Event() 
        t = threading.Thread(target=io_forwarder, args=(process_list,))
        t.start()
        
    # Listing of (rank, host, port) for all the processes
    all_procs = []
    # Listing of socket connections to all the processes
    sender_conns = []

    #logger.debug("Waiting for %d processes" % options.np)
    
    # Recieve listings from newly started proccesses phoning in
    for i in range(options.np):       
        sender_conn, sender_addr = s.accept()
        sender_conns.append( sender_conn )
        
        # Receiving data about the communicator, by unpacking the head etc.
        rank, command, data = get_raw_message(sender_conn)
        data = pickle.loads(data)
        (communicator, sender, tag, message) = data
        
        all_procs.append( message ) # add (rank,host,port) for process to the listing
    #logger.debug("Received information for all %d processes" % options.np)
    
    # Send all the data to all the connections, closing each connection afterwards
    COMM_ID = -1
    COMM_RANK = -1
    data = (COMM_ID, COMM_RANK, constants.TAG_INITIALIZING, all_procs)
    message = prepare_message(data, -1)
    for conn in sender_conns:
        utils.robust_send(conn, message)

    s.close()
    
    # Trap CTRL-C before we let processes loose on the world
    signal.signal(signal.SIGINT, signal_handler)
    
    
    # Wait for all started processes to die
    exit_codes = processloaders.wait_for_shutdown(process_list)    
    for conn in sender_conns: # if still up (shouldn't be)
        conn.close()        

    # Check exit codes from started processes
    any_failures = sum(exit_codes) is not 0
    if any_failures:
        logger.error("Some processes failed to execute, exit codes in order: %s" % exit_codes)
   
    if options.process_io == "asyncdirect":
        logger.debug("IO forward thread will be stopped")
        # Signal shutdown to io_forwarder thread
        io_shutdown_event.set()

        # Wait for the IO_forwarder thread to stop
        t.join()
        logger.debug("IO forward thread joined")

    sys.exit(1 if any_failures else 0)
