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
import os, subprocess, time
from mpi.logger import Logger
from mpi.exceptions import MPIException
from mpi import constants
import sys

def _islocal(host):
    return host == "localhost" or host == "127.0.0.1"

def popenssh(host, arguments, process_io, rank):
    """ Mixed Popen/SSH process starter. Uses Popen for localhost, otherwise SSH"""
    if _islocal(host):
        _ = popen(host, arguments, process_io, rank)
    else:
        ssh(host, arguments, process_io, rank)

# Let everyone see the same processes
global process_list, io_target_list
process_list = []
io_target_list = []

def ssh(host, arguments, process_io, rank):
    """Process starter using ssh through subprocess. No loadbalancing yet."""
    logger = Logger()

    # We join the sys.path here to allow user modifications to PYTHONPATH to take effect remotelyy
    python_path = os.path.dirname(os.path.abspath(__file__)) + "/../" + ":" + ":".join(sys.path)
    sshexec_str = "ssh %s \"PYTHONPATH=%s %s\"" % (host, python_path, ' '.join(arguments) )
    #logger.debug("Starting remote process: %s with process_io type %s" % (sshexec_str, process_io))

    if process_io in ['none', 'direct', 'remotefile']: # network is closed for i/o, nothing displayed or written on mpirun side. If remote_file, a file is created on the remote process machine only.
        target = None
    elif process_io == 'asyncdirect': # uses io forwarder and prints to console
        target = subprocess.PIPE
    elif process_io == 'localfile': # writes to a file on the mpirun machine only
        try:
            target = open(constants.DEFAULT_LOGDIR+"mpi.rank%s.log" % rank, "w")
            io_target_list.append(target)
        except:
            raise MPIException("Local directory not writeable - check that this path exists and is writeable:\n%s" % constants.DEFAULT_LOGDIR)
    else:
        raise MPIException("Unsupported I/O type: '%s'" % process_io)

    # Execute the ssh command in a subprocess
    p = subprocess.Popen(sshexec_str, shell=True, stdout=target, stderr=target)
    process_list.append(p)
    return p

def popen(host, arguments, process_io, rank):
    """ Process starter using subprocess. No loadbalancing yet. Process_io is ignored"""
    if _islocal(host):
        p = subprocess.Popen(arguments, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process_list.append(p)
        return p
    else:
        raise MPIException("This processloader can only start processes on localhost, '%s' specified." % host)

def terminate_children():
    for p in process_list:
        logger = Logger()
        logger.debug("Killing %s" % p)
        p.terminate()

def wait_for_shutdown(process_list):
    """
    Go through list of processes and make sure they all have terminated
    """
    logger = Logger()
    exit_codes = []
    while process_list:
        remove = []
        for p in process_list:
            returncode = p.poll()
            #logger.debug("Got return code: %s" % returncode)

            if returncode is None: # still alive
                pass
            elif returncode == 0: # exited correctly
                exit_codes += [returncode]
                remove.append(p)
                #process_list.remove( p )
                logger.debug("A process exited with a status of 0. And we have %i left." % ( len(process_list)-len(remove)))
            else: # error code
                exit_codes += [returncode]
                remove.append(p)
                #process_list.remove( p )
                logger.debug("A process exited with return code %d. And we have %i left." % (returncode, len(process_list)-len(remove)))

        # We remove outside iteration over list just to be safe
        for p in remove:
            process_list.remove( p )

        time.sleep(1)

    # Target list is empty unless the option process_io=localfile is specified, in
    # which case we close the filedescriptors of all the log files made
    for t in io_target_list:
        t.close()

    return exit_codes
