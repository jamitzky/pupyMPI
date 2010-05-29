# Small program to show the issue with bug in cPickle of Python 2.6.4
"""
http://bugs.python.org/issue7758
http://bugs.python.org/issue7455
"""

import cStringIO as io
import cPickle
import pickle

resp = 0
prompt = "Type 1 to use cPickle (should segfault) or 2 for ordinary pickle (should throw a proper exception)"
while not resp in ("1","2"):
    resp = raw_input(prompt)

if resp == "1":
    cPickle.load( io.StringIO( '0' ) )
else:
    pickle.load( io.StringIO( '0' ) )
