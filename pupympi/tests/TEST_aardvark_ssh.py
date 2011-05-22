#!/usr/bin/env python2.6
# meta-description: Test that should trigger the sshd connection limit on eg. Ubuntu
# meta-expectedresult: 0
# meta-minprocesses: 14

"""
Simple program to make sure that sshd is configured to allow enough connections
for the rest of the tests to run on localhost.

NOTE: If this test fails - especially if you see this error message
"ssh_exchange_identification: Connection closed by remote host"
go check your ssh configuration!

pupyMPI tests on localhost might need more than 20 processes each with their own
ssh connection.
On eg. Ubuntu the default is to allow something like 10 unauthorized connections
which is not always enough since many processes could be trying to authorize at
the same time.

The parameter that controls this is MaxStartups in /etc/ssh/sshd_config
With this default:
MaxStartups 10:30:60
ssh will allow 10 connections to queue up for auth and then with 30% probability
drop further connection attempts queueing. The probability of dropping rises
linearly until the ultimate maximum of 60 unauthorized connections is reached.
With this setting:
MaxStartups 100:1:100
ssh is configured to allow 100 pending connections and not drop anything since
max is also 100. This gives predictable behaviour which is preferred when testing
pupyMPI.

Again, if this test fails - maybe with this message hiding in the debug output:
"ssh_exchange_identification: Connection closed by remote host"
you should check your ssh configuration!
"""


from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

if size < 11:
    print "This test is meaningless with so few processes"

# Ensure that all 14 processes have indeed started
mpi.MPI_COMM_WORLD.barrier()

# Close the sockets down nicely
mpi.finalize()
