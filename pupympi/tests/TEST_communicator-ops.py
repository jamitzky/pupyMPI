#!/usr/bin/env python2.6
# meta-description: Test if communicator operations function. 
# meta-expectedresult: 0
# meta-minprocesses: 2

# Simple pupympi program to test all communicator ops

from mpi import MPI
from mpi import constants
from sys import stderr

mpi = MPI()

newgroup = mpi.MPI_COMM_WORLD.group()
mcw = mpi.MPI_COMM_WORLD

print "Testing communicator comm_create"
print "NEXT FOUR VALUES MUST BE IDENTICAL FOR EVERY PROCESS"
print "----------------------------------------------------"
newcomm_full = mpi.MPI_COMM_WORLD.comm_create(newgroup)
assert newcomm_full is not None
print "Communicator ID: %s. Created from mpi comm world." % newcomm_full.id

newcomm_full2 = mpi.MPI_COMM_WORLD.comm_create(newgroup)
assert newcomm_full2 is not None
print "Communicator ID: %s. Also created from mpi comm world." % newcomm_full2.id

newcomm_full3 = newcomm_full.comm_create(newgroup)
assert newcomm_full3 is not None
print "Communicator ID: %s. Split from the first mcw clone" % newcomm_full3.id

newcomm_full4 = newcomm_full2.comm_create(newgroup)
assert newcomm_full4 is not None
print "Communicator ID: %s. Split from the second mcw clone" % newcomm_full4.id

print "-- OK"

    
print "Testing communicator comm_free"
print "----------------------------------------------------"

newcomm_full4.comm_free() 
print "-- OK"

print "Testing communicator comm_dup"
print "----------------------------------------------------"

cloned_comm_of_mcw = mpi.MPI_COMM_WORLD.comm_dup()
assert cloned_comm_of_mcw is not None
assert cloned_comm_of_mcw.group() is newgroup
print "Cloned mcw: %s" % cloned_comm_of_mcw
print "-- OK"

print "Testing basic MCW clone communication abilities."
print "----------------------------------------------------"
if newcomm_full.rank() == 0:
    newcomm_full.send(1, "MSG", 1)
elif newcomm_full.rank() == 1:
    data = newcomm_full.recv(0, 1)
    assert data == "MSG"
else:
    pass # do nothing

print "Testing communicator comm_compare"
print "----------------------------------------------------"

assert mpi.MPI_COMM_WORLD.comm_compare(mcw) is constants.MPI_IDENT # test for object identity
assert mcw.comm_compare(newcomm_full) is constants.MPI_CONGRUENT # test that the underlying groups are identical

if mcw.rank() == 0: # more advanced testing now
    meandonegroup = newgroup.incl([0,1])
    oneandmegroup = newgroup.incl([1,0])
    me_group = newgroup.incl([0])
    
    meandonecomm = mcw.comm_create(meandonegroup)
    oneandmecomm = mcw.comm_create(oneandmegroup)
    me_comm = mcw.comm_create(me_group)
    assert meandonecomm.comm_compare(oneandmecomm) is constants.MPI_SIMILAR
    assert meandonecomm.comm_compare(me_comm) is constants.MPI_UNEQUAL
    
    # test for silliness
    a = "this is really not a communicator, sssssssh! we might fool it!"    
    assert meandonecomm.comm_compare(a) is constants.MPI_UNEQUAL
    
print "-- OK"


# FIXME: test comm_split when ready

# Close the sockets down nicely
mpi.finalize()
