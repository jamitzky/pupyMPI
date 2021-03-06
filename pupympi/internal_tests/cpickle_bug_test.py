# Small program to show the issue with bug in cPickle of Python 2.6.4
"""
http://bugs.python.org/issue7758
http://bugs.python.org/issue7455
http://bugs.python.org/issue7542
"""

import cStringIO as io
import cPickle
import pickle

resp = 0
prompt = "Type a to use cPickle (should segfault) or b for ordinary pickle (should throw a proper exception): "
while not resp in ("a","b"):
    resp = raw_input(prompt)

#if resp == "a":
#    cPickle.load( io.StringIO( '0' ) )
#else:
#    pickle.load( io.StringIO( '0' ) )

if resp == "a":
    cPickle.loads( '0')
else:
    pickle.loads( '0' )
