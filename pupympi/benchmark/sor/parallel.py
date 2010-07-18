#Sequential code for the eScience assignment in clustercomputing.
#Heat equation -- Successive over-relaxation (SOR)
#Version 1.1 October 12. 2009 - tested with Python 2.6.2 and Psyco 1.6

#Requires the python PyLab library:
#http://www.scipy.org/PyLab

#Uses python JIT compiler Psyco
#http://psyco.sourceforge.net/

import timer #Timer class - replaces standard time
import sorgraphics #Graphics class - visualizing the heat equation
import pylab as pl #Scientific module
from mpi import MPI # MPI module
from math import floor
try:
  # JIT compiler - not critical for correctness
  # NB. only avaliable for 32-bit architectures
  import psyco
  psyco.full()
  print 'Psyco installed!'
except:
  print 'No psyco installed - this will be slow!!!'

#This solves the system of partial differential equations
#Parameter is
#  data - the problem instance matrix with temperatures
def solve(data):
  global update_freq, mpi

  comm = mpi.MPI_COMM_WORLD
  rank = comm.rank()

  ROW_TAG = 50
  DELTA_TAG = 51

  if rank == 0:
  
  h=len(data)-1
  w=len(data[0])-1
  
  if rank == wsize - 1:
    h -= 1

  epsilon=.1*h*w
  delta=epsilon+1.
  cnt=update_freq-1
  while(delta>epsilon):
    delta=0.
    cnt=cnt+1
    if cnt==update_freq:
      if useGraphics:
        g.update(data)
      cnt=0
    # receive from neighbors
    if rank == 0:
        top_row = data[0]
    else:
        # top neighbor
        top_row = comm.recv(rank-1, ROW_TAG)

    if rank == wsize - 1:
        btm_row = data[-1]
    else:
        # bottom neighbor
        btm_row = comm.recv(rank+1, ROW_TAG)

    for y in range(1,h):
      for x in range(1,w):
        old=data[y,x]
        data[y,x]=.2*(data[y,x]+data[y-1,x]+data[y+1,x]+data[y,x-1]+data[y,x+1])
        delta+=abs(old-data[y,x])

    # send to neighbors
    if rank > 0:
        comm.isend(data[0], rank-1, ROW_TAG)
    if rank < wsize - 1:
        comm.isend(data[-1], rank+1, ROW_TAG)

    # reduceall epsilon
    delta = comm.allreduce(delta, sum)
    
    if cnt==update_freq:
        print "Rank %d: allreduce delta = %d" (rank, delta)

#Default problem size
xsize=500
ysize=500
useGraphics=False
i=0

for opt in pl.sys.argv:
    if opt == "--":
        i = 1
    elif i > 0 and not opt.startswith("-"):
        if i == 1:
            xsize = int(opt)
        if i == 2:
            ysize = int(opt)
        if i == 3:
            useGraphics = int(opt)
        if i > 3:
            print("Parameters <x-size> <y-size> <use graphics>")
            pl.sys.exit(-1)
        i+=1

mpi = MPI()
comm = mpi.MPI_COMM_WORLD
rank = comm.rank()
wsize = comm.size()

ymin = floor(rank * ysize / wsize)
ymax = floor((rank + 1) * ysize / wsize)

problem=pl.zeros((xsize,ymax-ymin),dtype=pl.float32)

if rank == 0:
    problem[0,1:-1]=40. #Top

if rank == wsize - 1:
    problem[-1]=-273.15 #Bottom

problem[0:-1,:1]=-273.15 #Left
problem[0:-1,-1:]=-273.15 #Right

print "My rank is %d - xsize:%d ysize:%d useGraphics:%d" % (rank, xsize, ymax-ymin, useGraphics)
print "My slice is (xmin,ymin,xmax,ymax) = (%d,%d,%d,%d)" % (0, floor(rank * ysize / wsize), -1, floor((rank + 1) * ysize / wsize))

update_freq=10
if useGraphics:
  g=sorgraphics.GraphicsScreen(xsize,ysize)

timer=timer.StopWatch()
timer.Start()

#Start solving the heat equation
# solve(problem)

mpi.finalize()

timer.Stop()
print "Solved the successive over-relaxation in %s" % (timer.timeString())

if useGraphics:
  timer.Sleep(5)
