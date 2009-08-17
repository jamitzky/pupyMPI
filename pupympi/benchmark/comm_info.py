#!/usr/bin/env python
# encoding: utf-8
"""
comm_info.py

per process settings

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

from common import gen_testset, gen_reductionset
 
w_num_procs = None          # number of procs in COMM_WORLD             
w_rank = None               # rank of actual process in COMM_WORLD      

NP = None                   # #processes participating in benchmarks    
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

# CHANGED disabled - its for mem handling.
# void* s_buffer;            # send    buffer                           
# assign_type* s_data;       # assign_type equivalent of s_buffer       
# int   s_alloc;             # #bytes allocated in s_buffer             
# void* r_buffer;            # receive buffer                           
# assign_type* r_data;       # assign_type equivalent of r_buffer       
# int   r_alloc;             # #bytes allocated in r_buffer             
# # IMB 3.1 <<  
# float max_mem, used_mem;   # max. allowed / used GBytes for all       
#                            # message  buffers                         
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
