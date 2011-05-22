"""
A simple server for testing performance with try/accept in receive loops

Connect to the server on the port specified and send an amount of data
terminated by a single line containing a dot (.) and a newline character.

First run the server will try to call accept() on the client socket and get an
exception before receiving data from the socket.

Second run the server will immediately receive on the client socket without
attempting an accept call.

Timings given are wall-clock totals for all data received in either loop.
"""

import socket
import time
import sys

host = 'localhost'
port = 36647
rx_sizes = [4096, 2048, 1024, 512, 256, 128, 64, 32, 16]
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, port))

s.listen(5)

print "rx_size,fast_mode,bytes,time"
for rx_size in rx_sizes:
    print >> sys.stderr, "Now listening on %s:%d with %d byte recv size" % (host, port, rx_size)
    client, address = s.accept()
    print >> sys.stderr, "Client connected."
    t0 = time.time()
    recv_bytes = 0
    while 1:
        try:
            client.accept()
        except socket.error, e:
            data = client.recv(rx_size)
            recv_bytes += len(data)
            if data == ".\n":
                client.close()
                break

    t1 = time.time()

    print >> sys.stderr, "Received %d bytes in %s seconds" % (recv_bytes, t1-t0)
    print "%d,%d,%d,%s" % (rx_size,0,recv_bytes,t1-t0)

    client, address = s.accept()
    print >> sys.stderr, "Client connected (in fast mode)."
    t0 = time.time()
    recv_bytes = 0
    while 1:
        data = client.recv(rx_size)
        recv_bytes += len(data)
        if data == ".\n":
            client.close()
            break

    t1 = time.time()

    print >> sys.stderr, "Received %d bytes in %s seconds (in fast mode)" % (recv_bytes, t1-t0)
    print "%d,%d,%d,%s" % (rx_size,1,recv_bytes,t1-t0)

s.close()
