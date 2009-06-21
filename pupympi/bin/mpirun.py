#!/usr/bin/env python2.6
# This is the main pupympi startup script. See the usage function
# for information about it

import mpi, sys

def usage():
    print """
    USAGE: 

    mpirun (pupympi) version %s.

    Syntax:
    ./mpirun [OPTIONS] [MPI_SCRIPT]

    Where [OPTIONS] can be of the following:

     --np N  : The number of processes to start
     --number-procs N : See above

     -d 
     --debug : Allows internal logging and printing for debugging purposes

    And [MPI_SCRIPT] is a python script to execute N versions of. If
    you don't give a [MPI_SCRIPT] you can specify the MPI program
    through the interactive python command line. 
    """ % mpi.__version__
    sys.exit()

if __name__ == "__main__":
    import getopt
    try:
        optlist, args = getopt.gnu_getopt(sys.argv[1:], 'np:hv', ['help','verbose','number-procs='])
    except getopt.GetoptError, err:
        print str(err)
        usage()

    np = 0
    debug = False
    verbose = False

    if not optlist:
        usage()

    for opt, arg in optlist:
        if opt in ("-h", "--help"):
            usage()
        
        if opt in ("-np", "--number-procs"):
            try:
                np = int(arg)
            except ValueError:
                print "Argument to %s should be an integer" % opt
                usage()

        if opt in ("-d", "--debug"):
            debug = True

        if opt in ("-v", "--verbose"):
            verbose = True

    for rank in range(np):
        p = Process(target=executeable)

