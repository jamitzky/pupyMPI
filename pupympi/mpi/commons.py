# Simple way to avoid the try-except import in every file. 

try:
    import numpy
except ImportError:
    numpy = None

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import yappi
except ImportError:
    yappi = None

try:
    import pupyprof
except ImportError:
    pupyprof = None
