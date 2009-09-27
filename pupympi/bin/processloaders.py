import sys, os, subprocess, select, time
from mpi.exceptions import MPIException
from mpi.logger import Logger

# TODO Output redirect. Log files?

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"
    
def popenssh(host, arguments, process_io, rank):
    """ Mixed Popen/SSH process starter. Uses Popen for localhost, otherwise SSH"""
    if _islocal(host):
        p = popen(host, arguments, process_io, rank)
    else:
        ssh(host, arguments, process_io, rank)

# Let everyone see the same processes
global process_list, io_target_list    
process_list = []
io_target_list = []

def ssh(host, arguments, process_io, rank):
    """Process starter using ssh through subprocess. No loadbalancing yet."""
    logger = Logger()
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../"
    sshexec_str = "ssh %s \"PYTHONPATH=%s %s\"" % (host, python_path, ' '.join(arguments) )
    logger.debug("Starting remote process: %s" % sshexec_str)
    
#    sys.stdout = open("/tmp/myoutput")
    if process_io in ['none', 'remote_file']: # network is closed for i/o, nothing displayed or written on mpirun side. If remote_file, a file is created on the remote process machine only.
        target = None
    elif process_io == 'pipe': # uses io forwarder and prints to console
        target = subprocess.PIPE
    elif process_io == 'filepipe': # writes to a file on the mpirun machine only
        target = open("/tmp/mpi.rank%s.log" % rank, "w") # FIXME temporary naming/handling/solution
        io_target_list.append(target)
    else:
        raise MPIException("Unsupported I/O type: '%s'" % process_io)

    # Execute the ssh command in a subprocess
    p = subprocess.Popen(sshexec_str, shell=True, stdout=target, stderr=target)
    process_list.append(p)

    return p
    
def popen(host, arguments, process_io, rank):
    """ Process starter using subprocess. No loadbalancing yet. Process_io is ignored"""
    logger = Logger()

    if _islocal(host):
        p = subprocess.Popen(arguments, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)

def terminate_children():
    sys.exit()

def wait_for_shutdown(process_list):
    """
    Go through list of processes and make sure they all have terminated
    """
    logger = Logger()
    exit_codes = []
    while process_list:
        for p in process_list:
            returncode = p.poll()
            #logger.debug("Got return code: %s" % returncode)

            if returncode is None: # still alive
                pass
            elif returncode == 0: # exited correctly
                logger.debug("A process exited with a status of 0. And we have %i left." % ( len(process_list)-1))
                exit_codes += [returncode]
                process_list.remove( p )
            else: # error code
                exit_codes += [returncode]
                process_list.remove( p )
                logger.debug("A process exited with return code %d. And we have %i left." % (returncode, len(process_list)-1 ))

        time.sleep(1)
    for t in io_target_list:
        t.close()
        
    return exit_codes