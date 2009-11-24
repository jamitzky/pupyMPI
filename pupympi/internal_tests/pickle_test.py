try:
    import cPickle as pickle
except ImportError:
    import pickle
from time import time

class A():
    def __init__(self):
        self.a = 1
        self.b = 2

d1 = (3, "A simple int")
d2 = (range(10), "A medium list")
d3 = (range(10000), "A large list")
d4 = ([A() for x in range(100)], "100 objects")
    
for data_struct in (d1,d2,d3,d4):
    data, data_desc = data_struct
    print "\n"*5
    print "="*80
    for iterations in range(1000, 500000, 100000):
        data = 'my test message'
        n = time()
        for i in range(iterations):
            p = pickle.dumps({'rank' : 1, 'tag' : 1, 'data' : data, 'communicator' : 3})
        t1 = time() - n
        
        n = time()
        for i in range(iterations):
            p = pickle.dumps((1, 1, data, 3))
        t2 = time() - n
        
        f = float(t1)/float(t2)
        print "Iterations %d, %s: tuple are %s times faster" % (iterations, data_desc, f)
    print "="*80