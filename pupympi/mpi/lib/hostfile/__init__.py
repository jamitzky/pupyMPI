from mpi.lib.hostfile.parser import parse_hostfile
from mpi.lib.hostfile.mappers import round_robin, HostfileMapException  

__all__ = ("parse_hostfile", "round_robin"  )

import unittest

class TestRoundRobin(unittest.TestCase):
    
    def setUp(self):
        # Generate a bunch of fake hostfile data. Just for run
        self.hostfile_info = []
        procs = 40
        for i in range(procs):
            self.hostfile_info.append({'host' : "myhost%d" % i, 'cpu' : 2, 'max_cpu' : 4})

    def test_invalid_overmapping(self):
        # 4 actual CPUs, each overmapping by 4 = 16 virutal
        self.assertRaises(HostfileMapException, round_robin, self.hostfile_info, 4, 16, 17, False)
        
    def test_more_cpus_than_ranks(self):
        expected_data = [('myhost0', 0), ('myhost1', 1), ('myhost2', 2), ('myhost3', 3)]
        data = round_robin(self.hostfile_info[:4], 8, 16, 4, False)
        self.assertEquals(data, expected_data)

    def test_overmapping(self):
        data = round_robin(self.hostfile_info[:2], 4, 8, 8, True)
        expected_data = [('myhost0', 0), ('myhost1', 1), ('myhost0', 2), ('myhost1', 3), ('myhost0', 4), ('myhost1', 5), ('myhost0', 6), ('myhost1', 7)]
        self.assertEquals(data, expected_data)

    def test_nodata(self):
        data = round_robin([], 0, 0, 8, True)
        expected_data = [('localhost', 0), ('localhost', 1), ('localhost', 2), ('localhost', 3), ('localhost', 4), ('localhost', 5), ('localhost', 6), ('localhost', 7)]
        self.assertEquals(data, expected_data)
        
if __name__ == '__main__':
    unittest.main()