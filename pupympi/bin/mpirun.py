#!/usr/bin/env python2.6
# This is the main pupympi startup script. See the usage function
# for information about it
"""
mpirun.py (pupympi) %s

Usage: ./mpirun.py [OPTION]... [PROGRAM]...
Start the program with pupympi

    -c | -np | --np <arg0>      The number of processes to run
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
    -hf | --host-file <arg0>    The host file where the processes should be
                                started. See the documentation for the proper
                                format. 
    -h | --help                 Display this help. 

Bugs should not be reported. But if you need to please call Frederik. He can be 
contacted between 2 and 5 in the middle of the night. 
""" 

import mpi, sys

def usage():
    print __doc__
    sys.exit()

def parse_hostfile(hostfile, rank):
    if not hostfile:
        # Fake it
        return {"host" : range(rank) ]
    else:
        fh = open(hostfile, "r")
        host_division = {}
        for line in rh.readlines():
            # We need a format for the hostfile
            pass

        fh.close()

        if len(host_division):
            return host_division

        raise IOError("No lines in your hostfile, or somethign else went wrong")

if __name__ == "__main__":
    import getopt
    try:
        optlist, args = getopt.gnu_getopt(sys.argv[1:], 'c:np:dvql:hf:h', ['np=','verbosity=','quiet','log-file=','host','host-file=','debug'])
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
        
        if opt in ("-c","-np", "--number-procs"):
            try:
                np = int(arg)
            except ValueError:
                print "Argument to %s should be an integer" % opt
                usage()

        if opt in ("-d", "--debug"):
            debug = True

        if opt in ("-v", "--verbosity"):
            verbosity = arg

        if opt in ("-q", "--quiet"):
            quiet = True

        if opt in ("-l", "--log-file"):
            logfile = arg

        if opt in ("-hf", "--host-file"):
            hostfile = arg

    # Manage the hostfile. The hostfile should properly return a host -> [ranks] structure
    # so we know how many processes to start on each machine. See the parse_hostfile 
    # function above.
    try:
        hosts = parse_hostfile(hostfile, rank)
    except IOError:
        print "Something bad happended when we tried to read the hostfile. "
        sys.exit()

    # Start a process for each rank. 
    for (host, ranks) in hosts:
        # Prepare the command line args for the subprocesses
        for rank in ranks:
            command = "%s --rank=%d --size=%d --verbosity=%d" % (sys.argv[-1], rank, np, verbosity)
            if quiet:
                command += " --quiet"

            if debug:
                command += " --debug"

            if logfile:
                command += " --log-file=%s" % logfile

            if host == "localhost":             # This should be done a bit clever
                from subprocess import Popen
                p = Popen(["/usr/bin/env python", arguments])
