#!/usr/bin/env python
# encoding: utf-8
"""
comm_info.py

per process settings

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""
import time
from common import gen_testset, gen_reductionset, N_BARR
from mpi import constants
 
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
s_data_generator = gen_testset # NEW: generator function

red_data_type = 'f'         # data type of reduced data                
op_type = None              # operation type                           
s_data_generator = gen_reductionset # NEW: generator function

pair0, pair1 = (0, 1)       # process pair                             
select_tag = False          # 0/1 for tag selection off/on             
select_source = False       # 0/1 for sender selection off/on          

clock_function = time.clock # set this to communicator.Wtime() for MPI time
                      
# # >> IMB 3.1   

# TODO Implement part or all of this.

# int n_lens;                # # of selected lengths by -msglen option  
# int* msglen;               # list of  "       "                  "    
# 
# int group_mode;            # Mode of running groups (<0,0,>0)         
# int n_groups;              # No. of independent groups                
# int group_no;              # own group index                          
# int* g_sizes;              # array of group sizes                     
# int* g_ranks;              # w_ranks constituting the groups          
# 
# int* sndcnt;               # send count argument for global ops.      
# int* sdispl;               # displacement argument for global ops.    
# int* reccnt;               # recv count argument for global ops.      
# int* rdispl;               # displacement argument for global ops.    

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
    for b in xrange(N_BARR):
        communicator.barrier()
    
def get_iter_single(iteration_schedule, size):
    return xrange(iteration_schedule[size] if iteration_schedule is not None else 50)