"""
client.py

...to go along with server
"""
import pdb

import Pyro.core

# you have to change the URI below to match your own host/port.
jokes = Pyro.core.getProxyForURI("PYROLOC://localhost:7767/jokegen")

pdb.set_trace()
def outoftopframe():
	#for debug testing
	a = 123
	b = "dipj"

	c = 0
	d = True
	a = 123
	b = "dipj"

	c = 0
	d = True

	e = "is my breakpoint"

	try:
		print jokes.joke("Irmen")
	except:
		print "Error caught"

	print "Nice exit"

outoftopframe()
