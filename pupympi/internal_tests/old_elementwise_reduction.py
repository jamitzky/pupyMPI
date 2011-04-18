"""
Testing various ways to apply an operation elementwise on a collection of sequences
Sequences can be everything iterable
"""
import numpy

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
    #print sequences
    reduced_results = map(operation,zip(*sequences))
    #print reduced_results

    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join

    return reduced_results

def mammy(sequences, operation):
    """
    mapping and zipping like there's no tomorrow,
    but with special treatment for numpy arrays using matrices
    """
    #print "type:%s type0:%s" % (type(sequences),type(sequences[0]))
    
    if isinstance(sequences[0], numpy.ndarray):
        m = numpy.matrix(sequences)
        #print "type:%s type0:%s" % (type(m),type(m[0]))
        res = m.min(0)
        #print "type:%s type0:%s" % (type(res),type(res[0]))
        reduced_results = res.A[0]
    else:
        reduced_results = map(operation,zip(*sequences))
            
    # Restore the type of the sequence
    if isinstance(sequences[0],str):
        reduced_results = ''.join(reduced_results) # join char list into string
    if isinstance(sequences[0],bytearray):
        reduced_results = bytearray(reduced_results) # make byte list into bytearray
    if isinstance(sequences[0],tuple):
        reduced_results = tuple(reduced_results) # join

    #print "type:%s type0:%s" % (type(reduced_results),type(reduced_results[0]))
    return reduced_results

def mammy2(sequences, operation):
    """
    mapping and zipping like there's no tomorrow,
    but with special treatment for numpy arrays using matrices
    """
    #print "type:%s type0:%s" % (type(sequences),type(sequences[0]))
    
    if isinstance(sequences[0], numpy.ndarray):
        #print "type:%s type0:%s" % (type(m),type(m[0]))
        #print "type:%s type0:%s" % (type(res),type(res[0]))
        reduced_results = numpy.matrix(sequences).min(0).A[0]
    else:
        reduced_results = map(operation,zip(*sequences))
            
        # Restore the type of the sequence
        if isinstance(sequences[0],str):
            reduced_results = ''.join(reduced_results) # join char list into string
        if isinstance(sequences[0],bytearray):
            reduced_results = bytearray(reduced_results) # make byte list into bytearray
        if isinstance(sequences[0],tuple):
            reduced_results = tuple(reduced_results) # join

    #print "type:%s type0:%s" % (type(reduced_results),type(reduced_results[0]))
    return reduced_results

def nummy(sequences, operation):
    """
    mapping and zipping like there's no tomorrow,
    but with special treatment for numpy arrays
    """
    #print "type:%s type0:%s" % (type(sequences),type(sequences[0]))
    if isinstance(sequences[0], numpy.ndarray):
        #print "type:%s type0:%s" % (type(m),type(m[0]))
        #print "type:%s type0:%s" % (type(res),type(res[0]))
        reduced_results = numpy.minimum.reduce(sequences)
    else:
        reduced_results = map(operation,zip(*sequences))
            
        # Restore the type of the sequence
        if isinstance(sequences[0],str):
            reduced_results = ''.join(reduced_results) # join char list into string
        if isinstance(sequences[0],bytearray):
            reduced_results = bytearray(reduced_results) # make byte list into bytearray
        if isinstance(sequences[0],tuple):
            reduced_results = tuple(reduced_results) # join

    #print "type:%s type0:%s" % (type(reduced_results),type(reduced_results[0]))
    return reduced_results

def mappy(sequences, operation):
    """
    NOTE: Mappy has been retired since it doesn't currently work
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

def numpy_generate_data(bytemultiplier,participants):
    """
    Generate the dataset externally from measured functions so that impact is not measured

    The bytemultiplier scales op the 50 int base to appropriate size
    Participants represent the number of sequences to reduce on
    """
    baserange = numpy.arange(50)
    
    #baserange = numpy.arange(50,dtype=numpy.float64)

    wholeset = []
    for p in range(participants):
        from copy import copy
        rang = copy(baserange)
        rang[p] = -42
        wholeset.append(rang)

    return wholeset

def runner(version):
    if version == 0:
       res = simple(testdata,MPI_min)
    elif version == 1:
        res = xsimple(testdata,MPI_min)
    elif version == 2:
        res = convoluted(testdata,MPI_min)
    elif version == 3:
        res = zippy(testdata,MPI_min)
    #elif version == 4:
    #    res = mappy(testdata,MPI_min)
    elif version == 4:
        res = mammy(testdata,MPI_min)
    elif version == 5:
        res = mammy2(testdata,MPI_min)
    elif version == 6:
        res = nummy(testdata,MPI_min)
    else:
        print "no version..."
    
    # DEBUG
    #print res



if __name__=='__main__':
    # How big should the data payload be
    bytemultiplier = 10
    # Participants (how wide is the payload)
    #participants = 2
    #participants = 5
    participants = 10       # Around 10 participants - nummy always wins
    
    #participants = 20      # Around 20 participants - mammy can beat zippy
    #participants = 40
    # Generate the data
    global testdata
    testdata = generate_data(bytemultiplier,participants)
    #testdata = numpy_generate_data(bytemultiplier,participants)
    
    # DEBUG
    #print numpytestdata

    runs = 1000
    

    from timeit import Timer
    t_simple = Timer("runner(0)", "from __main__ import runner")
    duration = t_simple.timeit(runs)
    print "simple \t\t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_xsimple = Timer("runner(1)", "from __main__ import runner")
    duration = t_xsimple.timeit(runs)
    print "xsimple \t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_convoluted = Timer("runner(2)", "from __main__ import runner")
    duration = t_convoluted.timeit(runs)
    print "convoluted \t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_zippy = Timer("runner(3)", "from __main__ import runner")
    duration = t_zippy.timeit(runs)
    print "zippy \t\t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_mammy = Timer("runner(4)", "from __main__ import runner")
    duration = t_mammy.timeit(runs)
    print "mammy \t\t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_mammy2 = Timer("runner(5)", "from __main__ import runner")
    duration = t_mammy2.timeit(runs)
    print "mammy2 \t\t took %f seconds meaning %f per call" % (duration, duration/runs)

    t_nummy = Timer("runner(6)", "from __main__ import runner")
    duration = t_nummy.timeit(runs)
    print "nummy \t\t took %f seconds meaning %f per call" % (duration, duration/runs)

    #t_mappy = Timer("runner(4)", "from __main__ import runner")
    #duration = t_mappy.timeit(runs)
    #print "Test took %f seconds meaning %f per call" % (duration, duration/runs)
