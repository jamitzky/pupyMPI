#Timer class for use with eScience assignment
#Version 1.1 October 12. 2009 - tested with Python 2.6.2 and Psyco 1.6

#Requires the python PyLab library:
#http://www.scipy.org/PyLab

#Uses python JIT compiler Psyco
#http://psyco.sourceforge.net/

import time #Standard Python time module
import pylab as pl #Scientific module
try:
  # JIT compiler - not critical for correctness
  # NB. only avaliable for 32-bit architectures
  import psyco
  psyco.full()
except:
  pass

class StopWatch:
  def __init__(self):
    self.start=self.stop=time.time()

  def Sleep(self, x):
    time.sleep(x)

  def Start(self):
    self.start=time.time()

  def Stop(self):
    self.stop=time.time()

  def readDays(self):
    return int((self.stop-self.start)/(24*60*60))

  def readHours(self):
    return int(((self.stop-self.start)/(60*60))%24)

  def readMinutes(self):
    return int((self.stop-self.start)/(60)%60)

  def readSeconds(self):
    return int(((self.stop-self.start))%60)

  def readmSeconds(self):
    return (self.stop-self.start)%1*1000

  def timeString(self):
    res=''
    if self.readDays()>0: res+=str(self.readDays())+" day(s), ";
    if self.readHours()>0: res+=str(self.readHours())+" hour(s), ";
    if self.readMinutes()>0: res+=str(self.readMinutes())+" min., ";
    if self.readSeconds()>0: res+=str(self.readSeconds())+" sec. and ";
    res+=str(self.readmSeconds())+" ms.";
    return res;
