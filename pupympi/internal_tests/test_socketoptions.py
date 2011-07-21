# Helper to test setting and getting socket options

import os
import socket
import tempfile

print "=== OS limits ==="
wmem_def = "cat /proc/sys/net/core/wmem_default"
wmem_max = "cat /proc/sys/net/core/wmem_max"
print wmem_def+':'
os.system(wmem_def)
print wmem_max+':'
os.system(wmem_max)

print "=== Python Unix socket stuff ==="
socketfile = tempfile.NamedTemporaryFile().name
unixsocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
unixsocket.bind(socketfile)
sndbuf = unixsocket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
rcvbuf = unixsocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
print "socket.SO_SNDBUF: %s" % sndbuf
print "socket.SO_RCVBUF (no effect): %s" % rcvbuf

"""
The SO_SNDBUF socket option does have an effect for Unix domain  sockets,  but
the  SO_RCVBUF  option  does  not.
- man 7 unix
"""

print "=== Python TCP socket stuff ==="
tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsocket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
tcpsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sndbuf = tcpsocket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
rcvbuf = tcpsocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
print "socket.SO_SNDBUF: %s" % sndbuf
print "socket.SO_RCVBUF: %s" % rcvbuf



solist = [x for x in dir(socket) if x.startswith('SO_')]
tcplist = [x for x in dir(socket) if x.startswith('TCP_')]

# what groups are there?
s = set()
for x in dir(socket):
    prefix = x.split('_')[0]
    s.add(prefix)
    