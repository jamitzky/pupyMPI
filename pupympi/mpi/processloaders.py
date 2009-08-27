import sys, os, subprocess, select, time
from mpi.exceptions import MPIException
from mpi.logger import Logger

# TODO Output redirect. Log files?

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"
    
def popenssh(host, arguments):
    """ Mixed Popen/SSH process starter. Uses Popen for localhost, otherwise SSH"""
    if _islocal(host):
        p = popen(host, arguments)
    else:
        ssh(host, arguments)

# Let everyone see the same processes
global process_list    
process_list = []

def ssh(host, arguments):
    """Process starter using ssh through subprocess. No loadbalancing yet."""
    logger = Logger()
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../"
    sshexec = ["ssh"] + [host] + ["PYTHONPATH=" + python_path ]+ arguments 
    logger.debug("Exec: %s" % (' '.join(sshexec)))
    # Execute the ssh command in a subprocess
    p = subprocess.Popen(sshexec, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process_list.append(p)
    return p
    
def popen(host, arguments):
    """ Process starter using subprocess. No loadbalancing yet"""
    logger = Logger()

    if _islocal(host):
        p = subprocess.Popen(arguments, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)

def wait_for_shutdown(process_list):
    """
    Go through list of processes and make sure they all have terminated
    """
    logger = Logger()
    while process_list:
        for p in process_list:
            returncode = p.poll()
            logger.debug("Got return code: %s" % returncode)

            if returncode is None: # still alive
                logger.debug("A process reports still alive")
            elif returncode == 0: # exited correctly
                logger.debug("A process exited with a status of 0.")
                process_list.remove( p )
            else: # error code
                process_list.remove( p )
                logger.debug("A process exited with return code %d." % (returncode))

        time.sleep(1)

#def wait_for_shutdown(process_list):
#    """
#    Go through list of processes and make sure they all have terminated
#    
#    NOTE: This function does not currently make sense to me. We go through all the
#    processes in the list and remove them if they are still running (poll() = None)
#    or if they have exited correctly (poll() = 0) but not if they returned status != 0
#    (which should be error).
#    Then we sleep and poll the erroneous ones again?
#    This does not make sense, if Chewbacca lives on Endor you must acquit!
#    """
#    logger = Logger()
#    while process_list:
#        for p in process_list:
#            returncode = p.poll()
#            logger.debug("Got return code: %s" % returncode)
#
#            if returncode is None: # still alive
#                logger.debug("Process was None, so it was just removed from the process list")
#                process_list.remove( p )
#            elif returncode == 0: # exited correctly
#                logger.debug("Process exited with a status of 0.")
#                process_list.remove( p )
#            else: # error
#                logger.debug("Process exited with status: %d" % returncode)
#
#        time.sleep(1)
