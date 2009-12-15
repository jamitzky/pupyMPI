#!/usr/bin/env python
# encoding: utf-8
"""
collective.py - collection of collective tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci

meta_has_meta = True
meta_separate_communicator = False
meta_requires_data_ranks_adjunct = False
meta_min_processes = 4

meta_schedule = {
    0: 1000,
    1: 1000,
    2: 1000,
    4: 1000,
    8: 1000,
    16: 1000,
    32: 1000,
    64: 1000,
    128: 1000,
    256: 1000,
    512: 1000,
    1024: 1000,
    2048: 1000,
    4096: 1000,
    8192: 1000,
    16384: 1000,
    32768: 1000,
    65536: 640,
    131072: 320,
    262144: 160,
    524288: 80,
    1048576: 40,
    2097152: 20,
    4194304: 10
}
def test_Bcast(size, max_iterations):
    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for r in xrange(max_iterations):
            my_data = data if ci.rank == root else "" # NOTE: probably superflous, discuss with Rune
            ci.communicator.bcast(root, my_data)
            
            # Switch root
            root = (root +1) % ci.num_procs
        
        # TODO: note the error below in categorizing (directly from Pallas code)
        # CHK_DIFF("Allgather",c_info, (char*)bc_buf+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs, ...

    # end of test
    
    # NOTE: We have to add one to size=0 since our MPI_bcast doesn't work with zero length data
    # FIXME: Rune?
    if size == 0: # Empty messages are not handled well in collective ops
        # Size 0 could follow from limit=0 in which case the testset contains nothing to slice        
        customset = ci.gen_testset(1)
        data = customset[0:size+1]
    else:        
        data = ci.data[0:size]
    #data = ci.data[0:size]
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # Doit
    Bcast(data, max_iterations)

    t2 = ci.clock_function()
    
    time = (t2 - t1)
    return time
    
def test_Allgather(size, max_iterations):
    def Allgather(data, datalen, max_iterations):
        """docstring for Allgather"""
        for r in xrange(max_iterations):
            # TODO: check if allgather verifies that the jth block size is modulo size
            
            # We continually move offset in the array taking turns sending each of
            # the num_procs chunks, to ensure things aren't cached well.
            # NOTE: This might seem superflous in Python but we want to compare against
            # Pallas on LAM fairly            
            offset = ((ci.rank+r) % ci.num_procs) * datalen       
            received = ci.communicator.allgather( data[offset:offset+datalen-1] )
    # end of test
    
    # Allgather is not valid for size < num_procs
    # FIXME: Find proper interpretation of allgather for small size
    if size < ci.num_procs:
        return -42
    
    data = ci.gen_testset(size*ci.num_procs)
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgather(data, (size*ci.num_procs), max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1

    return time

    
#def test_Allgatherv(size, max_iterations):
#    def Allgatherv(data, datalen, max_iterations):
#        """docstring for Allgather"""
#        for r in max_iterations:
#            # TODO check if allgather verifies that the jth block size is modulo size 
#            ci.communicator.allgatherv(data[ci.rank:ci.rank+size], size, ci.rdispl) # FIXME allgatherv signature may change 
#            # ierr = MPI_Allgatherv((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
#            #                       s_num,c_info->s_data_type,
#            #                       (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#            #                       c_info->reccnt,c_info->rdispl,
#            #                       c_info->r_data_type,
#            #                       c_info->communicator);
#
#            # FIXME defect detection and error handling
#
#    # end of test

    
def test_Alltoall(size, max_iterations):
    def Alltoall(data, datalen, max_iterations):
        """docstring for Alltoall"""
        for r in xrange(max_iterations):
            # TODO: Maybe some of this list comprehension can be moved out of loop
            #       for slightly faster benchmarking
            
            # alternate order of sending for each iteration to minimize cache hits
            received = ci.communicator.alltoall( [data[(i+r)%ci.num_procs] for i in range(ci.num_procs)] )
                  #             ierr = MPI_Alltoall((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
                  #                                 s_num,c_info->s_data_type,
                  # (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
                  #                                 r_num,c_info->r_data_type,
                  # c_info->communicator);
            # FIXME defect detection and error handling

    # end of test
    # Alltoall is not valid for size < num_procs
    #if size < ci.num_procs:
    if size == 0:
        return -42
    
    data = ci.gen_testset(size*ci.num_procs)
    #Prepack data into lists for nicer iteration
    data = [ data[offset*size:offset*size+size] for offset in range(ci.num_procs) ]
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Alltoall(data, size, max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time 
       
#def test_Alltoallv(size, max_iterations):
#    def Alltoallv(data, datalen, max_iterations):
#        pass
#        # for(i=0;i< ITERATIONS->n_sample;i++)
#        #           {
#        #             ierr = MPI_Alltoallv((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
#        #                                  c_info->sndcnt,c_info->sdispl,
#        #                                  c_info->s_data_type,
#        #                      (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        #                                  c_info->reccnt,c_info->rdispl,
#        #                                  c_info->r_data_type,
#        #                      c_info->communicator);
#        #             MPI_ERRHAND(ierr);
#        # 
#        #             CHK_DIFF("Alltoallv",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        #                      c_info->rank*size,
#        #                      0, c_info->num_procs*size, 1, 
#        #                      put, 0, ITERATIONS->n_sample, i,
#        #                      -2, &defect);
#        #           }
#        #         
#    # end of test
#    pass

def test_Scatter(size, max_iterations):
    def Scatter(data, datalen, max_iterations):
        current_root = 0
        for r in xrange(max_iterations):
            my_data = data if ci.rank == current_root else "" # NOTE: probably superflous, discuss with Rune
            ci.communicator.scatter(my_data, current_root)
            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
            
        #       for(i=0;i<ITERATIONS->n_sample;i++)
        #       {
        #           ierr = MPI_Scatter((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
        #                              s_num, c_info->s_data_type,
        #                    (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
        # // root = round robin
        #                              r_num, c_info->r_data_type, i%c_info->num_procs,
        #                              c_info->communicator);
        #           MPI_ERRHAND(ierr);
        #           CHK_DIFF("Scatter",c_info, 
        #                    (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
        #                    s_num*c_info->rank, size, size, 1, 
        #                    put, 0, ITERATIONS->n_sample, i,
        #                    i%c_info->num_procs, &defect);
        #         }
    # end of test
    # Alltoall is not valid for size < num_procs
    #if size < ci.num_procs:
    if size == 0:
        return -42
    
    data = ci.gen_testset(size*ci.num_procs)
    #Prepack data into lists for nicer iteration
    data = [ data[offset*size:offset*size+size] for offset in range(ci.num_procs) ]
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Scatter(data, size, max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time 

#def test_Scatterv(size, max_iterations):
#    def Scatterv(data, datalen, max_iterations):
#        pass
#        #       for(i=0;i<ITERATIONS->n_sample;i++)
#        #       {
#        #           ierr = MPI_Scatterv((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
#        #                               c_info->sndcnt,c_info->sdispl, c_info->s_data_type,
#        #                     (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        # // root = round robin
#        #                               r_num, c_info->r_data_type, i%c_info->num_procs,
#        #                               c_info->communicator);
#        #           MPI_ERRHAND(ierr);
#        #           CHK_DIFF("Scatterv",c_info, 
#        #                    (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        #                    c_info->sdispl[c_info->rank], size, size, 1, 
#        #                    put, 0, ITERATIONS->n_sample, i,
#        #                    i%c_info->num_procs, &defect);
#        #         }
#    # end of test
#    pass

def test_Gather(size, max_iterations):
    def Gather(data, datalen, max_iterations):
        pass
    # end of test
    pass

#def test_Gatherv(size, max_iterations):
#    def Gatherv(data, datalen, max_iterations):
#        pass
#        #       for(i=0;i<ITERATIONS->n_sample;i++)
#        #       {
#        #           ierr = MPI_Gather ((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
#        #                              s_num,c_info->s_data_type,
#        #                    (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        # // root = round robin
#        #                              r_num, c_info->r_data_type, i%c_info->num_procs,
#        #                              c_info->communicator);
#        #           MPI_ERRHAND(ierr);
#        # #ifdef CHECK
#        #      if( c_info->rank == i%c_info->num_procs )
#        #      {
#        #           CHK_DIFF("Gather",c_info, 
#        #                    (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs, 0,
#        #                    0, c_info->num_procs*size, 1, 
#        #                    put, 0, ITERATIONS->n_sample, i,
#        #                    -2, &defect);
#        #      }
#        # #endif
#        #         }
#    # end of test
#    pass

def test_Reduce(size, max_iterations):
    def Reduce(data, datalen, max_iterations):
        """docstring for Reduce"""
        for r in max_iterations:
            pass
            
                #           ierr = MPI_Reduce((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
                #                             (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
                #                             s_num,
                # c_info->red_data_type,c_info->op_type,
                # i1,c_info->communicator);
                #           MPI_ERRHAND(ierr);
                # 
                #             #ifdef CHECK
                #              if( c_info->rank == i1 )
                #              {
                #                   CHK_DIFF("Reduce",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs, 0,
                #                            size, size, asize, 
                #                            put, 0, ITERATIONS->n_sample, i,
                #                            -1, &defect);
                #              }
                #             #endif
                #         /*  CHANGE THE ROOT NODE */
                #         i1=(++i1)%c_info->num_procs;
    # end of test

    # end of test
    if size > 0 or size < 4:
        return 0 # hack to modify schedule for reduce operations
        
    #data = common.gen_testset(size)*ci.num_procs
    data = ci.gen_testset(size)*ci.num_procs
    ci.rdispl = 1 # FIXME not necessarily best
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Reduce(data, size, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/max_iterations

    return time    


def test_Reduce_scatter(size, max_iterations):
    def Reduce_scatter(data, datalen, max_iterations):
        pass
        #   for (i=0;i<c_info->num_procs ;i++)
        #     {
        #      IMB_get_rank_portion(i, c_info->num_procs, size, s_size, 
        #                       &pos1, &pos2);
        #      c_info->reccnt[i] = (pos2-pos1+1)/s_size;
        # #ifdef CHECK
        #      if( i==c_info->rank ) {pos=pos1; Locsize= s_size*c_info->reccnt[i];}
        # #endif
        #      }
        # 
        #   if(c_info->rank!=-1)
        #     {
        #       for(i=0; i<N_BARR; i++) MPI_Barrier(c_info->communicator);
        # 
        #       t1 = MPI_Wtime();
        #       for(i=0;i< ITERATIONS->n_sample;i++)
        #         {
        #           ierr = MPI_Reduce_scatter
        #                            ((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
        #                             (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
        #                             c_info->reccnt,
        #               c_info->red_data_type,c_info->op_type,
        #               c_info->communicator);
        #           MPI_ERRHAND(ierr);
        # 
        #           CHK_DIFF("Reduce_scatter",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
        #                     pos,
        #                     Locsize, size, asize,
        #                     put, 0, ITERATIONS->n_sample, i,
        #                     -1, &defect);
        # 
        #         }
        #       t2 = MPI_Wtime();
        #       *time=(t2 - t1)/ITERATIONS->n_sample;
        #     }
        #   else
        #     { 
        #       *time = 0.; 
        #     }
        # 
    # end of test
    if size > 0 or size < 4:
        return 0 # hack to modify schedule for reduce operations
    pass

def test_Allreduce(size, max_iterations):
    def Allreduce(data, datalen, max_iterations):
        pass
        # for(i=0;i< ITERATIONS->n_sample;i++)
        #   {
        #     ierr = MPI_Allreduce((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
        #                          (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
        #                          s_num,
        #                      c_info->red_data_type,c_info->op_type,
        #                      c_info->communicator);
        #     MPI_ERRHAND(ierr);
        # 
        #     CHK_DIFF("Allreduce",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs, 0,
        #              size, size, asize, 
        #              put, 0, ITERATIONS->n_sample, i,
        #              -1, &defect);
        # 
        #   }
        
    # end of test
    if size > 0 or size < 4:
        return 0 # hack to modify schedule for reduce operations
    pass

def test_Barrier(size, max_iterations):
    def Barrier(max_iterations):
        """docstring for Barrier"""
        for r in max_iterations:
            ci.communicator.barrier()
    # end of test

    if size is not 0: 
        return 0 # hack to modify schedule for barrier
    
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    barrier(max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/max_iterations

    return time