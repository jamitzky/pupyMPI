"""
Testing various ways to apply an operation elementwise on a collection of sequences
Sequences can be everything iterable
"""

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
    else:
        print "Hejhej"
    
    #res = reduce_elementwise(smallbase,min)
    #print res
    
    
if __name__=='__main__':
    # How big should the data payload be
    bytemultiplier = 10000
    # Participants (how wide is the payload)
    participants = 5
    # Generate the data
    global testdata
    testdata = generate_data(bytemultiplier,participants)
    
    from timeit import Timer
    t_simple = Timer("runner(0)", "from __main__ import runner")
    runs = 10
    duration = t_simple.timeit(runs)
    print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
    
