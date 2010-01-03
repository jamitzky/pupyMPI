#!/usr/bin/env python
# encoding: utf-8
"""
collective.py - collection of collective tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""
from mpi.operations import MPI_max, MPI_list_max

import comm_info as ci

meta_has_meta = True
meta_requires_data_ranks_adjunct = False
meta_min_processes = 4
meta_processes_required = -1

meta_schedule = {
    0: 10,
    1: 10,
    2: 10,
    4: 10,
    8: 10,
    16: 10,
    32: 10,
    64: 10,
    128: 10,
    256: 10,
    512: 10,
    1024: 10,
    2048: 10,
    4096: 10,
    8192: 10,
    16384: 10,
    32768: 10,
    65536: 5,
    131072: 5,
    262144: 5,
    524288: 5,
    1048576: 5,
    2097152: 5,
    4194304: 5
}
def test_Bcast(size, max_iterations):
    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for r in xrange(max_iterations):
            my_data = data if ci.rank == root else "" # NOTE: probably superflous, discuss with Rune
            ci.communicator.bcast(my_data, root)
            
            # Switch root
            root = (root +1) % ci.num_procs
        
        # TODO: note the error below in categorizing (directly from Pallas code)
        # CHK_DIFF("Allgather",c_info, (char*)bc_buf+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs, ...

    # end of test
    
    # NOTE: We have to add one to size=0 since our MPI_bcast doesn't work with zero length data
    # FIXME: Rune?
    if size == 0: # Empty messages are not handled well in collective ops
        # Size 0 could follow from limit=0 in which case the testset contains nothing to slice        
        size += 1 

    ci.synchronize_processes()

    t1 = ci.clock_function()

    # Doit
    Bcast(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    
    time = (t2 - t1)
    return time

# Goes to max 16384 on the cluster with 8 procs
def test_Allgather(size, max_iterations):
    def Allgather(data, max_iterations):
        """docstring for Allgather"""
        for r in xrange(max_iterations):
            # NOTE: Should we be concerned about having data cached? Is it a fair
            #       comparison? Shouldn't LAM MPI have cached similar sizes as us?
            received = ci.communicator.allgather( data )
    # end of test
    
    # Allgather is not valid for size < num_procs
    # FIXME: Find proper interpretation of allgather for small size
    if size < ci.num_procs:
        return -42
    
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgather(ci.data[:size], max_iterations)

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

# Goes to max 16384 on the cluster with 8 procs
def test_Alltoall(size, max_iterations):
    def Alltoall(data, max_iterations):
        """docstring for Alltoall"""
        for r in xrange(max_iterations):

            received = ci.communicator.alltoall(data)
                  #             ierr = MPI_Alltoall((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
                  #                                 s_num,c_info->s_data_type,
                  # (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
                  #                                 r_num,c_info->r_data_type,
                  # c_info->communicator);
        # end of test

    # Alltoall is not valid for size < numprocs
    if size < ci.num_procs:
        return -42
    
    #Prepack data into lists for nicer iteration
    # TODO: We send size/numprocs data to each process for now
    chunksize = size/ci.num_procs
    # each distinct chunk goes to a distinct process
    datalist = [ ci.data[(x*chunksize):(x*chunksize)+chunksize] for x in range(ci.num_procs) ]
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Alltoall(datalist, max_iterations)

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
    def Scatter(data, max_iterations):
        current_root = 0
        for r in xrange(max_iterations):
            my_data = data if ci.rank == current_root else None # NOTE: probably superflous, discuss with Rune
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
    
    # Scatter is not valid for size < numprocs
    if size < ci.num_procs:
        return -42
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Scatter(ci.data[:size], max_iterations)

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

# NOTE: Our gather currently only goes up to 1048576  and sometimes stall at 131072 or 32768(!)
def test_Gather(size, max_iterations):
    def Gather(data, max_iterations):
        current_root = 0
        for r in xrange(max_iterations):
            received = ci.communicator.gather(data, current_root)            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
    # end of test

    # Gather might not be valid for size zero
    # TODO: Check above assumption
    if size == 0:
        return -42
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    # TODO: All procs send size data to the reciever, maybe this is a bit much
    # for the upper limits of datasize, are we fine with a proc getting eg. 32x4 MB?
    # this could be scaled down as done for some of the other tests
    Gather(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

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
    def Reduce(data, max_iterations):
        """docstring for Reduce"""
        current_root = 0
        for r in xrange(max_iterations):
            # For the reduce operator we use pupyMPI's built-in max
            received = ci.communicator.reduce(data, MPI_list_max, current_root)            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
    # end of test

    #   /*  GET SIZE OF DATA TYPE */  
    #   MPI_Type_size(c_info->red_data_type,&s_size);
    #   if (s_size!=0) s_num=size/s_size;
    # 
    #   if(c_info->rank!=-1)
    #     {
    #       i1=0;
    # 
    #       for(i=0; i<N_BARR; i++) MPI_Barrier(c_info->communicator);
    # 
    #       t1 = MPI_Wtime();
    #       for(i=0;i< ITERATIONS->n_sample;i++)
    #         {
    #           ierr = MPI_Reduce((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
    #                             (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
    #                             s_num,
    #               c_info->red_data_type,c_info->op_type,
    #               i1,c_info->communicator);
    #           MPI_ERRHAND(ierr);
    # 
    # #ifdef CHECK
    #      if( c_info->rank == i1 )
    #      {
    #           CHK_DIFF("Reduce",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs, 0,
    #                    size, size, asize, 
    #                    put, 0, ITERATIONS->n_sample, i,
    #                    -1, &defect);
    #      }
    # #endif
    #     /*  CHANGE THE ROOT NODE */
    #     i1=(++i1)%c_info->num_procs;
    #         }
    #       t2 = MPI_Wtime();
    #       *time=(t2 - t1)/ITERATIONS->n_sample;
    #     }
    
    # Reduce might not be valid for size zero
    # TODO: Check assumption
    if size == 0:
        return -42
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Reduce(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

#def test_Reduce_scatter(size, max_iterations):
#    def Reduce_scatter(data, datalen, max_iterations):
#        pass
#        #   for (i=0;i<c_info->num_procs ;i++)
#        #     {
#        #      IMB_get_rank_portion(i, c_info->num_procs, size, s_size, 
#        #                       &pos1, &pos2);
#        #      c_info->reccnt[i] = (pos2-pos1+1)/s_size;
#        # #ifdef CHECK
#        #      if( i==c_info->rank ) {pos=pos1; Locsize= s_size*c_info->reccnt[i];}
#        # #endif
#        #      }
#        # 
#        #   if(c_info->rank!=-1)
#        #     {
#        #       for(i=0; i<N_BARR; i++) MPI_Barrier(c_info->communicator);
#        # 
#        #       t1 = MPI_Wtime();
#        #       for(i=0;i< ITERATIONS->n_sample;i++)
#        #         {
#        #           ierr = MPI_Reduce_scatter
#        #                            ((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
#        #                             (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        #                             c_info->reccnt,
#        #               c_info->red_data_type,c_info->op_type,
#        #               c_info->communicator);
#        #           MPI_ERRHAND(ierr);
#        # 
#        #           CHK_DIFF("Reduce_scatter",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
#        #                     pos,
#        #                     Locsize, size, asize,
#        #                     put, 0, ITERATIONS->n_sample, i,
#        #                     -1, &defect);
#        # 
#        #         }
#        #       t2 = MPI_Wtime();
#        #       *time=(t2 - t1)/ITERATIONS->n_sample;
#        #     }
#        #   else
#        #     { 
#        #       *time = 0.; 
#        #     }
#        # 
#    # end of test
#    if size > 0 or size < 4:
#        return 0 # hack to modify schedule for reduce operations
#    pass

def test_Allreduce(size, max_iterations):
    def Allreduce(data, max_iterations):
        for r in xrange(max_iterations):
            # For the allreduce operator we use Python built-in max
            received = ci.communicator.allreduce(data, max)            

    # end of test

    # Reduce might not be valid for size zero
    # TODO: Check assumption
    if size == 0:
        return -42
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Allreduce(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time
 
def test_Barrier(size, max_iterations):
    def Barrier(max_iterations):
        """docstring for Barrier"""
        for r in xrange(max_iterations):
            ci.communicator.barrier()
    # end of test

    if size is not 0: 
        return None # We don't care about barrier for increasing sizes
    
    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Barrier(max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time
