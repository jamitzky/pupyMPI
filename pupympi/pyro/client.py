"""
client.py

...to go along with server
"""

import Pyro.core

# you have to change the URI below to match your own host/port.
jokes = Pyro.core.getProxyForURI("PYROLOC://localhost:7767/jokegen")

try:
	print jokes.joke("Irmen")
except:
	print "Error caught"

print "Nice exit"
