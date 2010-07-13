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
  global update_freq
  h=len(data)-1
  w=len(data[0])-1
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
    for y in range(1,h):
      for x in range(1,w):
        old=data[y,x]
        data[y,x]=.2*(data[y,x]+data[y-1,x]+data[y+1,x]+data[y,x-1]+data[y,x+1])
        delta+=abs(old-data[y,x])

#Default problem size
xsize=500
ysize=500
useGraphics=True

if len(pl.sys.argv)>1:
  xsize=eval(pl.sys.argv[1])
  if len(pl.sys.argv)>2:
    ysize=eval(pl.sys.argv[2])
    if len(pl.sys.argv)>3: #use '0' or 'False', '1' or 'True'
      useGraphics=eval(pl.sys.argv[3])
      if len(pl.sys.argv)>4:
        print("Parameters <x-size> <y-size> <use graphics>")
        pl.sys.exit(-1)

problem=pl.zeros((xsize,ysize),dtype=pl.float32)
problem[0,1:-1]=40. #Top
problem[-1]=-273.15 #Bottom
problem[0:-1,:1]=-273.15 #Left
problem[0:-1,-1:]=-273.15 #Right

update_freq=10
if useGraphics:
  g=sorgraphics.GraphicsScreen(xsize,ysize)

timer=timer.StopWatch()
timer.Start()

#Start solving the heat equation
solve(problem)

timer.Stop()
print "Solved the successive over-relaxation in %s" % (timer.timeString())

if useGraphics:
  timer.Sleep(5)
