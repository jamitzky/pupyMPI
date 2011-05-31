#Graphics class for use with eScience assignment
#Heat equation
#Version 1.0 October 12. 2009 - tested with Python 2.6.2 and Psyco 1.6

#Requires the python PyLab library:
#http://www.scipy.org/PyLab

#Uses python JIT compiler Psyco
#http://psyco.sourceforge.net/

import pylab as pl #Scientific module
try:
  # JIT compiler - not critical for correctness
  # NB. only avaliable for 32-bit architectures
  import psyco
  psyco.full()
except:
  pass

class GraphicsScreen:
  def __init__(self, xsize, ysize):
    self.image=pl.zeros((ysize,xsize,3),dtype=pl.float32)
    pl.ion()

  def update(self, data):
    blue=pl.less(data,0.) # Fill in True where less than 0.0
    red=~blue # Reverse of the above
    #Blue
    self.image[...,2][blue]=pl.minimum(pl.absolute(pl.divide(data[blue],255.)),1.)
    #Red -- Max 40C, so we increase the intensity of the red color 6 times
    self.image[...,0][red]=pl.minimum(1.,pl.divide(pl.multiply(data[red],6.),255.))
    pl.imshow(self.image)
    pl.draw()
