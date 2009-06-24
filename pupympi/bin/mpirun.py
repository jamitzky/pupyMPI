#!/usr/bin/env python2.6
# This is the main pupympi startup script. See the usage function
# for information about it

import mpi, sys

def usage():
    print """
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
    """ % mpi.__version__
    sys.exit()

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

    # Here comes some nasty code. We'll fork the processes. 


    # FIXME: We should not use threads to start the processes. A fork should do this better 
    for rank in range(np):
        # Prepare the command line args for the subprocesses
        command = "/usr/bin/env python %s --rank=%d --size=%d --verbosity=%d" % (sys.argv[-1], rank, np, verbosity)
        if quiet:
            command += " --quiet"

        if debug:
            command += " --debug"

        if logfile:
            command += " --log-file=%s" % logfile

        import os
        pid = os.fork()
        if pid == 0:
            os.system( command )
