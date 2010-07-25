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
def solve(data, rboffset):
  global update_freq, mpi, epsilon

  comm = mpi.MPI_COMM_WORLD
  rank = comm.rank()

  BLACK_ROW_TAG = 50
  RED_ROW_TAG = 51
  DELTA_TAG = 52
  GRAPHICS_DATA_TAG = 53

  y0 = 0

  h=len(data)
  w=len(data[0])-1
  
  if rank == 0: # Do not update first row
    y0 = 1
    rboffset = not rboffset # Also, begin at different offset ;-)
  
  if rank == wsize - 1: # Do not update last row
    h -= 1

  print "[%d] Solve for x0=%d y0=%d h=%d w=%d" % (rank, 1+rboffset, y0, h, w)

  # Send initial black points
  if 0 < rank:
    tx1 = comm.isend(data[0], rank-1, BLACK_ROW_TAG)
  if wsize - 1 > rank:
    tx2 = comm.isend(data[-1], rank+1, BLACK_ROW_TAG)

  delta=epsilon+1.
  cnt=update_freq-1
  while(delta>epsilon):
    delta=0.
    cnt=cnt+1
    x0 = 1+rboffset

    # Update graphics (rank 0 only!) {{{
    # XXX This is horribly inefficient. Don't use this for anything else than debugging!
    if cnt==update_freq and useGraphics:
      cnt=0
      if 0==rank:
          for y in range(0,len(data)):
            wholeproblem[y] = data[y]

          for n in range(1,comm.size()):
            ndata = comm.recv(n, GRAPHICS_DATA_TAG)
            for ny in range(0,len(ndata)):
              y += 1
              wholeproblem[y] = ndata[ny]

          g.update(wholeproblem)
      else:
          comm.isend(data, 0, GRAPHICS_DATA_TAG)
    # }}}

    # Receive black points
    if rank == 0:
        top_row = data[0]
    else:
        rx1 = comm.irecv(rank-1, BLACK_ROW_TAG)

    if rank == wsize - 1:
        btm_row = data[-1]
    else:
        rx2 = comm.irecv(rank+1, BLACK_ROW_TAG)

    # Update red points
    for y in range(y0+1,h-1):
      for x in range(x0,w,2):
        old=data[y,x]
        data[y,x]=.2*(data[y,x]+data[y-1,x]+data[y+1,x]+data[y,x-1]+data[y,x+1])
        delta+=abs(old-data[y,x])
      if x0 == 1:
        x0 = 2
      else:
        x0 = 1

    # Complete receive of black points
    if 0 < rank:
        top_row = rx1.wait()
    if rank < wsize-1:
        btm_row = rx2.wait()

    # Update last and first red row
    y = h-1
    for x in range(x0,w,2):
      old=data[y0,x]
      data[y0,x]=.2*(data[y0,x]+top_row[x]+data[y0+1,x]+data[y0,x-1]+data[y0,x+1])
      delta += abs(old-data[y0,x])
    for x in range(2-int(rboffset),w,2):
      old=data[y,x]
      data[y,x]=.2*(data[y,x]+data[y-1,x]+btm_row[x]+data[y,x-1]+data[y,x+1])
      delta += abs(old-data[y,x])

    # Send/receive red points
    if 0 < rank:
      tx1 = comm.isend(data[0], rank-1, RED_ROW_TAG)
      rx1 = comm.irecv(rank-1, RED_ROW_TAG)
    else:
      top_row = data[0]
    if wsize - 1 > rank:
      tx2 = comm.isend(data[-1], rank+1, RED_ROW_TAG)
      rx2 = comm.irecv(rank+1, RED_ROW_TAG)
    else:
      btm_row = data[-1]

    # Switch x0 to opposite of initial
    x0 = 1+(not rboffset)

    # Update black points
    for y in range(y0+1,h-1):
      for x in range(x0,w,2):
        old=data[y,x]
        data[y,x]=.2*(data[y,x]+data[y-1,x]+data[y+1,x]+data[y,x-1]+data[y,x+1])
        delta+=abs(old-data[y,x])
      if x0 == 1:
        x0 = 2
      else:
        x0 = 1

    # Complete receive of red points
    if 0 < rank:
        top_row = rx1.wait()
    if rank < wsize-1:
        btm_row = rx2.wait()

    # Update last and first black row
    y = h-1
    for x in range(x0,w,2):
      old=data[y0,x]
      data[y0,x]=.2*(data[y0,x]+top_row[x]+data[y0+1,x]+data[y0,x-1]+data[y0,x+1])
      delta += abs(old-data[y0,x])
    for x in range(1+(rboffset),w,2):
      old=data[y,x]
      data[y,x]=.2*(data[y,x]+data[y-1,x]+btm_row[x]+data[y,x-1]+data[y,x+1])
      delta += abs(old-data[y,x])

    # Send black points
    if 0 < rank:
      tx1 = comm.isend(data[0], rank-1, BLACK_ROW_TAG)
    if rank < wsize - 1:
      tx2 = comm.isend(data[-1], rank+1, BLACK_ROW_TAG)

    # reduceall epsilon
    owndelta = delta
    delta = comm.allreduce(delta, sum)

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
epsilon=.1*(xsize-1)*(ysize-1)

problem=pl.zeros((ymax-ymin,xsize),dtype=pl.float32)

problem[:,:1]=-273.15 #Left
problem[:,-1:]=-273.15 #Right

if rank == 0:
    if useGraphics:
        wholeproblem=pl.zeros((ysize,xsize),dtype=pl.float32)
    problem[0,1:-1]=40. #Top

if rank == wsize - 1:
    problem[-1]=-273.15 #Bottom

print "My rank is %d - xsize:%d ysize:%d useGraphics:%d" % (rank, xsize, ymax-ymin, useGraphics)
print "My slice is (xmin,ymin,xmax,ymax) = (%d,%d,%d,%d)" % (0, floor(rank * ysize / wsize), -1, floor((rank + 1) * ysize / wsize))

update_freq=10
if 0==rank and useGraphics:
  g=sorgraphics.GraphicsScreen(xsize,ysize)

timer=timer.StopWatch()
timer.Start()

print "solving with rb offset %d" % (ymin % 2)

#Start solving the heat equation
solve(problem, int(ymin % 2)==1)

mpi.finalize()

timer.Stop()
print "Solved the successive over-relaxation in %s" % (timer.timeString())

if 0==rank and useGraphics:
  timer.Sleep(5)
