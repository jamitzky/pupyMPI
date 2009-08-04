"""
firstpyrotest.py

Testing Pyro communication among multiple processes
"""
import pdb

import Pyro.core
import Pyro.naming # For naming server

first = False

class Node(Pyro.core.ObjBase):
        def __init__(self):
                Pyro.core.ObjBase.__init__(self)
        def starter(self, name):
                return "Sorry "+name+", I don't do no nothing."

Pyro.core.initServer()


daemon=Pyro.core.Daemon()

try:
	ns=Pyro.naming.NameServerLocator().getNS() # Find naming server
except Error, e:
	first = True
	print "Error was: " + e


if first:
	print "here we should start a naming server"
else:
	daemon.useNameServer(ns) # Use the naming server


uri=daemon.connect(JokeGen(),"jokegen")

print "The daemon runs on port:",daemon.port
print "The object's uri is:",uri

daemon.requestLoop()
