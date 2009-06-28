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
contacted between 2 and 5 in the middle of the night. In the unlikely event
that he does not respond, please visit Rune at his home address - just bang the
door until he wakes up.
""" 

import mpi, sys, os

def usage():
    print __doc__
    sys.exit()

def parse_hostfile(hostfile, size):
	# NOTE: Size is ignored, I think this function should only parse, and deliver list of tuples of the form (hostname, hostparameters_in_dict)
	#   then according to what how many procs are needed and what kind of mapping is selected we can map that list into something nice
    # NOTE: Standard port below and maybe other defaults should not be hardcoded here
    # (defaults should probably be a parameter for this function)
    defaults = {"cpu":"1","max_cpu":"1024","port":"14000"}
    malformed = False
    
    if not hostfile:
        print "File not found"
        # NOTE: Here we can: fake it by defaulting, search in some standard dir or crap out
        #return [("localhost", range(size) )]
    else:
        fh = open(hostfile, "r")
        hosts = []        
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
                        specified[key] = val
                        #NOTE: Should check for value type here (probably non-int = malformed for now)
                
                hosts += [(hostname, specified)]

        fh.close()        

        if len(hosts):
        	# uncomment if you wanna see the format
        	#for (hName, hDict) in hosts:
        		#print hName
        		#print hDict
        	return hosts
        else:
            raise IOError("No lines in your hostfile, or something else went wrong")
            
def map_hostfile(hosts, np=1, type="rr"):
	# Assign ranks and host to all processes
	# NO MAPPING IS DONE YET - HAS TO CONFORM TO NEEDED DATASTRUCTURE
	if type == "rr": # Round-robin assigning
		i = 0
	    while np <> 0:
	    	(hostname,params) = hosts[i]
	    	# DO ACTUAL MAPPING HERE
	        np -= 1
	else: # Exhaustive assigning
		i = 0
	    while np <> 0:
	    	(hostname,params) = hosts[i]
	    	# DO ACTUAL MAPPING HERE
	        np -= 1


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
        hosts = parse_hostfile(hostfile, np)
    except IOError:
        print "Something bad happended when we tried to read the hostfile. "
        sys.exit()

    # Start a process for each rank. 
    for (host, ranks) in hosts:
        # Prepare the command line args for the subprocesses
        for rank in ranks:
            # This should be rewritten to be nicer
            executeable = sys.argv[-1]
            if not executeable.startswith("/"):
                executeable = os.path.join( os.getcwd(), sys.argv[-1])

            arguments = "--rank=%d --size=%d --verbosity=%d" % (rank, np, verbosity)
            if quiet:
                arguments += " --quiet"

            if debug:
                arguments += " --debug"

            if logfile:
                arguments += " --log-file=%s" % logfile

            if host == "localhost":             # This should be done a bit clever
                from subprocess import Popen
                p = Popen(["python", executeable, arguments])
