#!/usr/bin/env python2.6
#
# Copyright 2010 Rune Bromer, Asser Schroeder Femoe, Frederik Hantho and Jan Wiberg
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
import sys, os, copy, signal, select, time, threading
from optparse import OptionParser, OptionGroup

# Allow the user to import mpi without specifying PYTHONPATH in the environment
mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

import processloaders

from mpi import dill

from mpi.logger import Logger
from mpi.network import utils
from mpi.network.utils import create_random_socket, get_raw_message, prepare_message
from mpi import constants
from mpi.lib import hostfile
from mpi.network.utils import pickle

def write_cmd_handle(all_procs, filename=None):
    import sys

    if not filename:
        # Generate a file and write to that one
        import tempfile
        _, filename = tempfile.mkstemp(prefix="pupy")

    data = {
        'procs' : all_procs,
        'args' : sys.argv,
    }

    fh = open(filename, "wb")
    pickle.dump(data, fh, pickle.HIGHEST_PROTOCOL)

    fh.close()
    return filename

def parse_options(start_mode):
    usage = 'usage: %prog [options] arg'
    parser = OptionParser(usage=usage, version="pupyMPI version %s" % (constants.PUPYVERSION))

    if start_mode == "normal":
        parser.add_option('-c', '--np', dest='np', type='int', help='The number of processes to start.')

    # Hostfile information grouped together.
    parser_hf_group = OptionGroup(parser, "Hostfile",
            "Settings relating to mapping the starting processes to hosts. This is very important if you want optimal performance from your cluster. Optimal mapping will ensure that proper intra connects are used whenever possible and that slower nodes in the cluster will get mapped to fewer ranks.")

    parser_hf_group.add_option('--host-file', dest='hostfile', default="hostfile", help='Path to the host file defining all the available machines the processes should be started on. If not given, all processes will be started on localhost')
    parser_hf_group.add_option('--host-file-scheduler', dest='hostmap_scheduler', default='round_robin',
        help="The mapper from available hosts to (host, rank) pairs. Builtin options are (round_robin, greedy). Defaults to %default. It is also possible to specify a custom mapper in the format for X.Y where X is the Python module to import (hence it must be in the path) and Y is the actual function to use. See the manual for how to write you own mappers.")
    parser_hf_group.add_option('--host-file-sections', dest='hostfile_sections', help='A comma seperated list with the sections in the hostfile to use. This acts as a filter, so if not given all sections in the hostfile will be used. See the manual for more information about the hostfile format and possibilities.')
    parser_hf_group.add_option('--host-file-disable-overmapping', dest='disable_overmapping', default=False, action="store_true", help="Disable overmapping of processes to CPUs. This means that the system will not start if the hostfile does not provide sufficient hosts to contain the system.")

    parser.add_option_group(parser_hf_group)

    # Add logging and debugging options
    parser_debug_group = OptionGroup(parser, "Logging and debugging",
            "Use these settings to control the level of output to the program. The --debug and --quiet options can't be used at the same time. Trying to will result in an error.")
    parser_debug_group.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to %default.')
    parser_debug_group.add_option('-d', '--debug', dest='debug', action='store_true', help='Give you a lot of input')

    parser_debug_group.add_option('-q', '--quiet', dest='quiet', action='store_true', help='Give you no input')
    parser_debug_group.add_option('-l', '--logdir', dest='logdir', default=constants.DEFAULT_LOGDIR, help='Which directory the system should log to. Defaults to %default(.log). System logging includes traces from yappi or pupyprof and benchmark results')
    parser.add_option_group( parser_debug_group )

    parser_utils_group = OptionGroup(parser, "Utilities", "Settings for handling utilities. See the manual for a description or bin/utils/ for the actual utilities.")
    parser_utils_group.add_option('--cmd-handle', dest='cmd_handle', help="Path to where mpirun.py should place the run handle file (for utility usage). ")
    parser_utils_group.add_option('--disable-utilities', dest='disable_utilities', action='store_true', default=False)
    parser.add_option_group( parser_utils_group )

    # Add advanced options
    parser_adv_group = OptionGroup(parser, "Advanced options",
            "Be careful. You could do strange things here.")
    parser_adv_group.add_option('--remote-python', dest='remote_python', default="`which python2.6`", help='Path to Python 2.6 on remote hosts. Defaults to  %default')
    parser_adv_group.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh and popen (local only). Defaults to %default')
    parser_adv_group.add_option('--single-communication-thread', dest='single_communication_thread', action='store_true', help="Use this if you don't want MPI to start two different threads for communication handling. This will limit the number of threads to 3 instead of 4.")
    parser_adv_group.add_option('--disable-full-network-startup', dest='disable_full_network_startup', action='store_true', help="Do not initialize a socket connection between all pairs of processes. If not a second chance socket pool algorithm will be used. See also --socket-pool-size")
    parser_adv_group.add_option('--socket-pool-size', dest='socket_pool_size', type='int', default=20, help="Sets the size of the socket pool. Only used it you supply --disable-full-network-startup. Defaults to %default")
    parser_adv_group.add_option('--x-forward', dest='x_forward', default=False, action='store_true', help='Turn on X forwarding. Used when you need a pupyMPI process to use X, eg. for graphical output. Defaults to %default')
    parser_adv_group.add_option('--process-io', dest='process_io', default="direct", help='How to forward I/O (stdout, stderr) from remote process. Options are: none, direct, asyncdirect, localfile or remotefile. Defaults to %default')
    parser_adv_group.add_option('--enable-profiling', dest='enable_profiling', action='store_true', help="Whether to enable profiling of MPI scripts. Profiling data are stored in ./logs/pupympi.profiling.rank<rank>. Defaults to off.")
    parser_adv_group.add_option('--disable-unixsockets', dest='unixsockets', default=True, action='store_false', help="Switch to turn off the optimization using unix sockets instead of tcp for intra-node communication")
    parser_adv_group.add_option('--socket-poll-method', dest='socket_poll_method', default=False, help="Specify which socket polling method to use. Available methods are epoll (Linux only), kqueue (*BSD only), poll (most UNIX variants) and select (all operating systems). Default behaviour is to attempt to use either epoll or kqueue depending on the platform, then fall back to poll and finally select.")
    parser_adv_group.add_option('--yappi', dest='yappi', action='store_true', help="Whether to enable profiling with Yappi. Defaults to off.")
    parser_adv_group.add_option('--yappi-sorttype', dest='yappi_sorttype', help="Sort type to use with yappi. One of: name (function name), ncall (call count), ttotal (total time), tsub (total time minus subcalls), tavg (total average time)")
    parser_adv_group.add_option('--settings', dest='settings', default=None, help="A comma separated list of files of settings objects, overriding the default one. If you supply several files they will be parsed and imported one by one overriding each other. This menas that the last file take priority. ")
    parser.add_option_group( parser_adv_group )

    try:
        options, args = parser.parse_args()

        if options.debug and options.quiet:
            parser.error("options --debug and -quiet are mutually exclusive")

        if start_mode == "normal" and options.np is None:
            parser.error("You need to specify the number of processes to start with -c or --np.")

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

def communicate_startup(no_procs, ssocket, resume_state=None):
    """
    This methods listen on a server sockets for a number of processes
    to return with their main socket information. Once every process
    have returned, the data is gathered and broadcasted back. This
    way, each process will have information on how to contact each other.
    """
    # Listing of (rank, host, port) for all the processes
    all_procs = []
    handle_procs = []
    # Listing of socket connections to all the processes
    sender_conns = []

    conn_idx = {}

    # Recieve listings from newly started proccesses phoning in
    for i in range(no_procs):
        sender_conn, sender_addr = ssocket.accept()
        sender_conns.append( sender_conn )

        # Receiving data about the communicator, by unpacking the head etc.
        rank, command, tag, ack, comm_id, _, data = get_raw_message(sender_conn)
        message = pickle.loads(data)

        # Add the connection by the rank.
        conn_idx[rank] = sender_conn

        # FIXME: Is this right?
        all_procs.append( message[:4] ) # add (rank,host,port, unix_socket_filepath, sec_comp) for process to the listing
        handle_procs.append( message )

    # Send all the data to all the connections, closing each connection afterwards
    for rank in conn_idx:
        conn = conn_idx[rank]

        session = None
        if resume_state:
            # The session is already pickled. So we handle this as a simple string. This way we
            # can send the data normally.
            session = resume_state['procs'][rank]

        data = (all_procs, session)

        header,payloads = prepare_message(data, -1, comm_id=-1, tag=constants.TAG_INITIALIZING)
        utils.robust_send_multi(conn, [header]+payloads)

    return all_procs, handle_procs, sender_conns

def signal_handler(signal, frame):
    """
    TODO: Fix this to work if no all processes are living at call-time
    """
    print 'Interrupt signal trapped - attempting to nuke children. You may want to verify manually that nothing is hanging.'
    COMM_ID = -1
    COMM_RANK = -1
    data = (COMM_ID, COMM_RANK, constants.TAG_SHUTDOWN, all_procs)
    header,payloads = prepare_message(data, constants.CMD_ABORT)
    for conn in sender_conns:
        utils.robust_send_multi(conn, [header]+payloads)
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

def determine_start_type():
    import sys

    filename = None

    for parameter in sys.argv[1:]:
        if not parameter.startswith("-"):
            filename = parameter

    if not filename:
        return None

    try:
        dill.load(open(filename, 'r'))
        return "resume"
    except Exception as e:
        return "normal"

if  __name__ == "__main__":
    start_type = determine_start_type()

    # Parse the options. The run type will disable some parameters.
    options, args, user_options, executeable = parse_options(start_type) # Get options from clint

    # If we are resuming a job we need to parse the handle file. This will tell us
    # the state of the instance for each rank. And it will tell us how many processes
    # we should start :) The handle is in the 'executeable' variable.
    resume_handle = None
    if start_type == "resume":
        resume_handle = dill.load(open(executeable, "r"))

        # Set the number of ranks on the options object so the startup can continue.
        options.np = len(resume_handle['procs'])

    # Start the logger
    logger = Logger(os.path.join(options.logdir,"mpi"), "mpirun", options.debug, options.verbosity, options.quiet)

    # Map processes/ranks to hosts/CPUs
    hostfilemapper = hostfile.mappers.find_mapper(options.hostmap_scheduler)

    limit_to = []
    if options.hostfile_sections:
        limit_to = [s.strip() for s in options.hostfile_sections.split(",")]

    parsed_hosts, cpus, max_cpus = hostfile.parse_hostfile(options.hostfile,limit_to=limit_to)
    mappedHosts = hostfilemapper(parsed_hosts, cpus, max_cpus, options.np, overmapping=not options.disable_overmapping)

    s, mpi_run_hostname, mpi_run_port = create_random_socket() # Find an available socket
    s.listen(5)

    # Whatever is specified at cli is chosen as remote start function (popen or ssh for now)
    remote_start = getattr(processloaders, options.startup_method)

    # List of process objects (instances of subprocess.Popen class)
    process_list = []

    if resume_handle:
        executeable = "mpi/migrate.py"

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
            "--logdir=%s" % options.logdir,
            "--start-type=%s" % start_type,
            "--settings=%s" % options.settings
    ]

    if options.socket_poll_method:
        global_run_options.append('--socket-poll-method=%s' % options.socket_poll_method)

    if options.disable_full_network_startup:
        global_run_options.append('--disable-full-network-startup')

    if not options.unixsockets:
        global_run_options.append('--disable-unixsockets')

    if options.enable_profiling:
        global_run_options.append('--enable-profiling')

    if options.yappi:
        global_run_options.append('--yappi')

    if options.yappi_sorttype:
        global_run_options.append('--yappi-sorttype=%s' % options.yappi_sorttype)

    if options.disable_utilities:
        global_run_options.append('--disable-utilities')

    for flag in ("quiet", "debug"):
        value = getattr(options, flag, None)
        if value:
            global_run_options.append("--"+flag)

    # Start a process for each rank on the host
    for (host, rank) in mappedHosts:
        run_options = copy.copy(global_run_options)
        run_options.append("--rank=%d" % rank)

        # Adding user options. GNU style says this must be after the --
        run_options.append( "--" )
        run_options.extend( user_options )

        # Now start the process and keep track of it
        p = remote_start(host, run_options, options.x_forward, options.process_io, options.logdir, rank )
        process_list.append(p)

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

    all_procs, handle_procs, sender_conns = communicate_startup(options.np, s, resume_handle)

    s.close()

    # Trap CTRL-C before we let processes loose on the world
    signal.signal(signal.SIGINT, signal_handler)

    if not options.disable_utilities: # This very verbose check is important. If not set, the value will be None.
        cmd_handle = write_cmd_handle(handle_procs, filename=options.cmd_handle)
        print "Process handle written (use the utility scripts to interact with the running system) to: %s" % cmd_handle

    # Wait for all started processes to die
    exit_codes = processloaders.wait_for_shutdown(process_list)
    for conn in sender_conns: # if still up (shouldn't be)
        conn.close()

    # Check exit codes from started processes
    if any(exit_codes):
        logger.error("Some processes failed to execute, exit codes in order: %s" % exit_codes)

    if options.process_io == "asyncdirect":
        logger.debug("IO forward thread will be stopped")
        # Signal shutdown to io_forwarder thread
        io_shutdown_event.set()

        # Wait for the IO_forwarder thread to stop
        t.join()
        logger.debug("IO forward thread joined")

    sys.exit(int(any(exit_codes)))
