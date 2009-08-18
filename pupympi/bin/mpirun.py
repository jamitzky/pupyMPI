#!/usr/bin/env python2.6
import sys, os, socket
from optparse import OptionParser, OptionGroup
import select

from mpi import processloaders 
from mpi.processloaders import shutdown 
from mpi.logger import Logger
from mpi.tcp import get_socket
from mpi.lib.hostfile import parse_hostfile, map_hostfile
import threading

try:
    import cPickle as pickle
except ImportError:
    import pickle

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

def io_forwarder(list):
    logger = Logger()
        
    # Return open pipes of all processes in the process_list
    def get_list(process_list):
        pipes = []
        for p in process_list:
            if p.stderr:
                pipes.append(p.stderr)
            
            if p.stdout:
                pipes.append(p.stdout)
        return pipes
    
    # Allow destructive operations on copy of process_list
    #list = copy.deepcopy(process_list)
    # ...but it seems we just want the shallow ref
    pipes = get_list(list)

    # print lines from a filehandle
    def print_fh(fh):
        if not fh:
            return 

        try:
            lines = fh.readlines()
            for line in lines:
                if line:
                    print line.strip("\n")
        except Exception, e:
            Logger().error("print_fh: %s" % e.message)
    
    # Check on processes unless process_list was empty
    while list:
        logger.debug("In IO gather loop")
        readlist, _, _ =  select.select(pipes, [], [], 1.0)
        for fh in readlist:
            print_fh(fh)

        # Test if anyone is read
        for p in list:
            returncode = p.poll()
            if returncode is not None:
                list.remove(p)

                if returncode != 0:
                    logger.error("A child returned with an errorcode: %s" % returncode)
                else:
                    logger.debug("Child exited normally")

                print_fh(p.stderr)
                print_fh(p.stdout)

<<<<<<< /home/fred/Diku/ppmpi/code/pupympi/bin/mpirun.py
        pipes = get_list(list)
=======
            pipes = get_list(list)
    
    logger.debug("IO gather loop DONE DEAD")
>>>>>>> /tmp/mpirun.py~other.e8tuj9

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

    process_list = []

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

        p = remote_start(host, run_options)
        process_list.append(p)
            
        logger.debug("Process with rank %d started" % rank)

    # Start a thread to handle io forwarding
    t = threading.Thread(target=io_forwarder, args=(process_list,)).start()
        
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
    shutdown()

