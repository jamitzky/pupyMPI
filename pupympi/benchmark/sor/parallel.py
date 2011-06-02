#Sequential code for the eScience assignment in clustercomputing.
#Heat equation -- Successive over-relaxation (SOR)
#Version 1.1 October 12. 2009 - tested with Python 2.6.2 and Psyco 1.6
#Version 1.2 February 24. 2011 - tested with Python 2.6.6

#Requires the python PyLab library:
#http://www.scipy.org/PyLab

#Uses python JIT compiler Psyco
#http://psyco.sourceforge.net/

import time
import sys
import math
import pylab #Scientific module for visualisation and numpy array operations

import sorgraphics #Graphics class - visualizing the heat equation

from mpi import MPI # MPI module

class StopWatch:
    def __init__(self):
        self.start=self.stop=time.time()

    def Sleep(self, x):
        time.sleep(x)

    def Start(self):
        self.start=time.time()

    def Stop(self):
        self.stop=time.time()

    def readDays(self):
        return int((self.stop-self.start)/(24*60*60))

    def readHours(self):
        return int(((self.stop-self.start)/(60*60))%24)

    def readMinutes(self):
        return int((self.stop-self.start)/(60)%60)

    def readSeconds(self):
        return int(((self.stop-self.start))%60)

    def readmSeconds(self):
        return (self.stop-self.start)%1*1000

    def timeString(self):
        res=''
        if self.readDays()>0: res+=str(self.readDays())+" day(s), ";
        if self.readHours()>0: res+=str(self.readHours())+" hour(s), ";
        if self.readMinutes()>0: res+=str(self.readMinutes())+" min., ";
        if self.readSeconds()>0: res+=str(self.readSeconds())+" sec. and ";
        res+=str(self.readmSeconds())+" ms.";
        return res;


# Solve the system locally and communicate
def solve(rank, world_size, local_state, offset, epsilon, update_frequency, useGraphics, comm):
    """
    ISSUES
    - We send whole borders for now instead of skipping off color
    - In fairness to the sequential version, we need to gather results after delta condition has been triggered
    """
    
    # Setup graphics display if responsible for it and needed
    if 0==rank and useGraphics:
        g=sorgraphics.GraphicsScreen(xsize,ysize)
    
    # Tags to filter communication
    BLACK_ROW_TAG = 50
    RED_ROW_TAG = 51
    DELTA_TAG = 52
    GRAPHICS_DATA_TAG = 53
  
    # Who's at the ends
    top = 0
    bottom = world_size - 1
  
    # Neighbours
    upper = rank - 1 if rank != top else 0 # 0 has itself as upper
    lower = rank + 1 if rank != bottom else rank # max has itself as lower
    
    # Local problem size including borders
    height = len(local_state)
    width = len(local_state[0]) 
       
    delta = epsilon + 1
    iteration = 1
       
    while(delta > epsilon):
        iteration += 1

        # Save old state for delta computation
        old_local_state = local_state.copy()
        
        ### Calculate red
        for y in xrange(1,height-1): # all rows minus borders
            rowoffset = (y-1+offset) % 2
            for x in xrange(1+rowoffset,width-1,2): # all red points minus borders
                # update point
                local_state[y,x] = 0.2*(local_state[y,x]+local_state[y-1,x]+local_state[y+1,x]+local_state[y,x-1]+local_state[y,x+1])
        
        ### Sync red borders
        
        # Send border up
        if rank != top:
            comm.send(local_state[1],upper,tag=RED_ROW_TAG)
        # Send border down
        if rank != bottom:
            comm.send(local_state[height-2],lower,tag=RED_ROW_TAG)
        
        # Get (red) borders
        red_recv_requests = []
        if rank != top:
            upper_red_req = comm.irecv(upper,tag=RED_ROW_TAG)
            red_recv_requests.append(upper_red_req)
        if rank != bottom:
            lower_red_req = comm.irecv(lower,tag=RED_ROW_TAG)
            red_recv_requests.append(lower_red_req)
            
        # wait for red requests to fininsh
        all_ready = False
        while not all_ready:
            all_ready = comm.testall(red_recv_requests)
            time.sleep(0.1)
        
        # Update local state with red values
        if rank != top:
            local_state[0] = upper_red_req.wait()
        # Send border down
        if rank != bottom:
            local_state[height-1] = lower_red_req.wait()

        
        ### Calculate black
        for y in xrange(1,height-1): # all rows minus borders
            rowoffset = (y+offset) % 2
            for x in xrange(1+rowoffset,width-1,2): # all black points minus borders
                # update point
                local_state[y,x] = 0.2*(local_state[y,x]+local_state[y-1,x]+local_state[y+1,x]+local_state[y,x-1]+local_state[y,x+1])

        ### Sync black borders
        
        # Send border up
        if rank != top:
            comm.send(local_state[1],upper,tag=BLACK_ROW_TAG)
        # Send border down
        if rank != bottom:
            comm.send(local_state[height-2],lower,tag=BLACK_ROW_TAG)
        
        # Get (black) borders
        black_recv_requests = []
        if rank != top:
            upper_black_req = comm.irecv(upper,tag=BLACK_ROW_TAG)
            black_recv_requests.append(upper_black_req)
        if rank != bottom:
            lower_black_req = comm.irecv(lower,tag=BLACK_ROW_TAG)
            black_recv_requests.append(lower_black_req)
            
        # wait for black requests to fininsh
        all_ready = False
        while not all_ready:
            all_ready = comm.testall(black_recv_requests)
            time.sleep(0.1)
        
        # Update local state with black values
        if rank != top:
            local_state[0] = upper_black_req.wait()
        if rank != bottom:
            local_state[height-1] = lower_black_req.wait()

        # Check delta
        # NOTE: do we want to abs here?
        local_delta = (old_local_state - local_state).sum()
        delta = comm.allreduce(abs(local_delta), sum)
        
        if update_frequency != 0 and (iteration % update_frequency) == 0:
            # Gather global state
            # NOTE: Processes slice shared borders away. Top and bottom are special
            if rank == top:
                local_states = comm.gather(local_state[0:-1],top)
            elif rank == bottom:
                local_states = comm.gather(local_state[1:],top)
            else:
                local_states = comm.gather(local_state[1:-1],top)
            
            # Display global state
            if rank == top:
                global_state = pylab.array([i for sublist in local_states for i in sublist])

                print "Global state h:%i, w:%i type:%s subtype:%s" % (len(global_state), len(global_state[0]), type(global_state), type(global_state[0]))
                print "Local state h:%i, w:%i" % (len(local_state), len(local_state[0]))
                
                print "going epsilon:%f, delta:%f iteration:%i" % (epsilon,delta,iteration)
                if useGraphics:
                    g.update(global_state)
            
            



def setup_problem(rank, world_size, xsize, ysize, epsilonFactor):
    """    
    instantiate the 2d problem model
    each process only models the local area plus borders
    
    rank 0 additionally models the global state
    
    ISSUES
    - To be fair we should have rank 0 model global state and then transmit proper parts to everyone
    
    NOTE: Slack could be better distributed than everything on bottom process
    """
    
    epsilon = epsilonFactor * (xsize-1) * (ysize-1)
    #epsilon = epsilonFactor * xsize * ysize
    
    ymin = math.floor(rank * ysize / world_size)

    
    local_y = ysize // world_size
    
    # if problem size (heightwise) is not divisible by np there will be some slack
    slack = ysize % world_size        
    if slack and rank == world_size - 1:
        # Bottom process picks up the slack
        local_y += slack
    
    # Fill out local state
    # Add +2 rows to represent border state
    borders = 2
    if rank == world_size - 1 or rank == 0:
        # Top and bottom only have one shared border
        borders = 1
        
    local_state=pylab.zeros((local_y+borders,xsize),dtype=pylab.float32)

    global_state = []
    if rank == 0:
        local_state[0]=40. #Top border

        global_state = pylab.zeros((ysize,xsize),dtype=pylab.float32)

    if rank == world_size - 1:
        local_state[-1]=-273.15 #Bottom border

    local_state[:,0]=-273.15 # Left border
    local_state[:,-1:]=-273.15 # Right border
    
    rboffset = (int(ymin % 2) == 1)

    return (local_state, global_state, rboffset, epsilon)


if __name__ == "__main__":
    
    # Initialize MPI
    mpi = MPI()

    ### Setup parameters
    
    #Default problem size
    xsize=64
    ysize=64
    useGraphics=False
    
    epsilonFactor = 0.1
    #epsilonFactor = 0.01

    update_freq = 10
    update_freq = 0 # Zero means no updating
    
    useGraphics = 0
    
    args = sys.argv[1:]
    if len(args) > 2:
        try:
            xsize = int(args[0])
            ysize = int(args[1])
            useGraphics = bool(int(args[2]))
        except:
            print("Parameters <x-size> <y-size> <use graphics> <epsilon-factor>, must be convertable to <int> <int> <bool> <float>")
            mpi.finalize()
            sys.exit(-1)
            
        if len(args) > 3:
            try:
                epsilonFactor = float(args[3])
            except:
                print("Parameters <x-size> <y-size> <use graphics> <epsilon-factor>, must be convertable to <int> <int> <bool> <float>")
                mpi.finalize()
                sys.exit(-1)
    else:
        print("Parameters <x-size> <y-size> <use graphics> <epsilon-factor>")
        mpi.finalize()
        sys.exit(-1)
        
    comm = mpi.MPI_COMM_WORLD
    rank = comm.rank()
    world_size = comm.size()
    
    (local_state, global_state, rboffset, epsilon) = setup_problem(rank, world_size, xsize, ysize,epsilonFactor)
    
    # odd number of rows and odd rank means local state starts with a black point instead of red    
    rboffset = (rank % 2) * (ysize % 2)
    
    print "Rank:%i solving global x*y:%i*%i, local x*y:%i*%i, epsilonFactor:%.4f graphics:%s rb offset %d" % (rank,xsize,ysize, len(local_state), len(local_state[0]), epsilonFactor,("ON" if useGraphics else "OFF"),rboffset)

    timer=StopWatch()
    timer.Start()

    #Start solving the heat equation
    solve(rank, world_size, local_state, rboffset, epsilon, update_freq, useGraphics, comm)

    mpi.finalize()

    timer.Stop()
    print "Solved the successive over-relaxation in %s" % (timer.timeString())

    if 0==rank and useGraphics:
        dummy = raw_input("enter to clear canvas")
        

