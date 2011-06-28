#!/usr/bin/env python
# encoding: utf-8
"""
comm_info.py

per process settings at top, and assist functions at bottom
"""
import time, array, string
from mpi import constants
 
N_BARR = 2                  # Number of calls to barrier deemed neccessary for sync
 
mpi = None                  # MPI object instance
w_num_procs = None          # number of procs in COMM_WORLD             
w_rank = None               # rank of actual process in COMM_WORLD      

NP = None                   # processes participating in benchmarks    
topology = "Cartesian"      # NEW: topologytype
px, py = (None, None)       # processes are part of px x py topology    

communicator = None         # underlying communicator for benchmark(s)  

num_procs = None            # number of processes in communicator
rank = None                 # rank of actual process in communicator    

s_data_type = 'b'           # data type of sent data                    
r_data_type = 'b'           # data type of received data                

red_data_type = 'f'         # data type of reduced data                
op_type = None              # operation type                           

pair0, pair1 = (0, 1)       # process pair                             
select_tag = False          # 0/1 for tag selection off/on             
select_source = False       # 0/1 for sender selection off/on          

clock_function = time.time # NEW: set this to communicator.Wtime() for MPI time, or time.time() for an alternative timer.
data = None                 # NEW: Stores fixed data set
reduce_data = None
sndcnt, sdispl, reccnt, rdispl = (0,0,0,0)  # send and displacement for global ops NOTE: snd-, and reccnt not presently used.


def log(str):
    if rank == 0:
        print str

def get_srcdest_paired():
    if rank == pair0:
        dest = pair1
    elif rank == pair1:
        dest = pair0
    else:
        raise Exception("Pair values not as expected, pair0 %s, pair1 %s and rank %s" % (pair0, pair1, rank))
                
    source = dest if select_source else constants.MPI_SOURCE_ANY 
    
    return (source, dest)
    
def get_tags_single():
    """docstring for get_tag_single"""
    return (1, 1 if select_tag else constants.MPI_TAG_ANY)
    
def synchronize_processes():
    """docstring for barrier"""
    for _ in xrange(N_BARR):
        communicator.barrier()
    
def gen_reduce_testset(size):
    """
    Generate a testset to use in reduction operations.
    
    NOTE: We use 32 bit floats even though this might not be the native float
          size in Python. This is to match IMB where MPI_FLOAT is specified
          which is 32 bit.
    """
    import numpy
    
    # Sanity check. The size parameter is in bytes, and as we store
    # 32 bit floats we should have at least 4 bytes and always a
    # multipla of 4.
    if size < 4:
        return None
    if not num_procs > 1:
        print "gen_reduce_testset called with illegal number of processes (np:%s)" % num_procs
        return None
    
    array_length = size*num_procs / 4
        
    return numpy.arange(array_length, dtype=numpy.float32)
    
baseset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def gen_testset(size):
    """
    Generates a byte array of size*num_procs.
    Used for single and parallel ops.
    We stick to letters even though more bytes could be represented in a bytearray
    since this makes it easier on the eyes when debugging.
    
    TODO: This might be is an inefficient way of generating a large bytearray
          potentially of size 4M * 32 procs, so consider other methods
    """
    if not num_procs > 1:
        print "gen_testset called with illegal number of processes (np:%s)" % num_procs
        return None

    baseset = string.letters # Nicely visible in debug output
    l = len(baseset)
    data = bytearray([ baseset[i%l] for i in xrange(0,size*num_procs) ])
    return data

def gen_testset_old(size):
    """
    Generates test data of type array (byte) in the asked-for size.
    This function remains from when we supported python 2.5 (no bytearray)
    """

    data = array.array('b')
    for x in xrange(0, size*num_procs):
        data.append(ord(baseset[x % len(baseset)])) # Fast generation of data
    return data
