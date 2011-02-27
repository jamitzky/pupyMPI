"""
Testing various ways to apply an operation elementwise on a collection of sequences
Sequences can be everything iterable
"""

#from mpi.collective.operations import MPI_min

def MPI_min(input_list):
    """
    Returns the minimum element in the list.
    """
    return min(input_list)

def simple(sequences, operation):
    """
    Original, no frills
    """                
    reduced_results = []
    no_seq = len(sequences) # How many sequences
    seq_len = len(sequences[0]) # How long is a sequence
    for i in range(seq_len):
        try:
            temp_list = [ sequences[m][i] for m in range(no_seq) ] # Temp list contains i'th element of each subsequence
        except IndexError, e:
            # If any sequence is shorter than the first one an IndexError will be raised
            raise Exception("Whoops, seems like someone tried to reduce on uneven length sequences")
        # Apply operation to temp list and store result
        reduced_results.append(operation(temp_list))
        
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
        
    return reduced_results

def xsimple(sequences, operation):
    """
    using xrange instead of range seems to give a slight advantage
    (note that this will disappear in python2.7 or 3.1 whenever they made range behave properly)
    """                
    reduced_results = []
    no_seq = len(sequences) # How many sequences
    seq_len = len(sequences[0]) # How long is a sequence
    for i in xrange(seq_len):
        try:
            temp_list = [ sequences[m][i] for m in xrange(no_seq) ] # Temp list contains i'th element of each subsequence
        except IndexError, e:
            # If any sequence is shorter than the first one an IndexError will be raised
            raise Exception("Whoops, seems like someone tried to reduce on uneven length sequences")
        # Apply operation to temp list and store result
        reduced_results.append(operation(temp_list))
        
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
        
    return reduced_results

def convoluted(sequences, operation):
    """
    all about the list comprehensions
    """                
    reduced_results = []
    no_seq = len(sequences) # How many sequences
    seq_len = len(sequences[0]) # How long is a sequence
    
    reduced_results = [ operation([ sequences[m][i] for m in xrange(no_seq) ]) for i in xrange(seq_len) ]
    
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
        
    return reduced_results

def zippy(sequences, operation):
    """
    mapping and zipping like there's no tomorrow
    """
    print sequences
    reduced_results = map(operation,zip(*sequences))
    print reduced_results
    
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
        
    return reduced_results

def mappy(sequences, operation):
    """
    mapping and zipping like there's no tomorrow
    """
    reduced_results = map(operation,*sequences)
    
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join
        
    return reduced_results

def generate_data(bytemultiplier,participants):
    """
    Generate the dataset externally from measured functions so that impact is not measured
    
    The bytemultiplier scales op the 50 char base string to appropriate size
    Participants represent the number of sequences to reduce on
    """    
    basestring = "yadunaxmefotimesniggaibeatwhereibeatnahmeanfoooool"
    
    wholeset = []
    for p in range(participants):
        payload = basestring[:p]+'A'+basestring[p+1:]
        wholeset.append(payload*bytemultiplier)
    
    return wholeset

def runner(version):
    if version == 0:
       res = simple(testdata,min)
    elif version == 1:
        res = xsimple(testdata,min)
    elif version == 2:
        res = convoluted(testdata,min)
    elif version == 3:
        res = zippy(testdata,MPI_min)
    elif version == 4:
        res = mappy(testdata,MPI_min)
    else:
        print "no version..."
    
    print res
        
    
    
if __name__=='__main__':
    # How big should the data payload be
    bytemultiplier = 2
    # Participants (how wide is the payload)
    participants = 4
    # Generate the data
    global testdata
    testdata = generate_data(bytemultiplier,participants)
    
    runs = 1

    from timeit import Timer
    t_simple = Timer("runner(0)", "from __main__ import runner")
    duration = t_simple.timeit(runs)
    print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
    
    t_xsimple = Timer("runner(1)", "from __main__ import runner")
    duration = t_xsimple.timeit(runs)
    print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
    
    t_convoluted = Timer("runner(2)", "from __main__ import runner")
    duration = t_convoluted.timeit(runs)
    print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
    
    t_zippy = Timer("runner(3)", "from __main__ import runner")
    duration = t_zippy.timeit(runs)
    print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
    
    #t_mappy = Timer("runner(4)", "from __main__ import runner")
    #duration = t_mappy.timeit(runs)
    #print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
