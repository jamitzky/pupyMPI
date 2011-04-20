"""
Testing various ways to apply an operation elementwise on a collection of sequences
Sequences can be everything iterable
"""
import string
import copy
import time
import numpy
from contextlib import contextmanager

#from mpi.collective.operations import MPI_min

# Auxillary timing function
@contextmanager
def timing(printstr="time", repetitions=0, swallow_exception=False):
    start = time.time()
    try:
        yield
    except Exception, e:
        print "ERROR: " + str(e)
        if not swallow_exception:
            raise
    finally:
        total_time = time.time() - start
        if repetitions > 0:
            avg_time = total_time / repetitions
            print "%s: %f / %f sec." % (printstr, total_time, avg_time)
        else:
            print "%s: %f sec." % (printstr, total_time)


# Auxillary MPI operations
def MPI_min(input_list):
    """
    Returns the minimum element in the list.
    """
    return min(input_list)


# Auxillary MPI operations
def MPI_sum(input_list):
    """
    Returns the minimum element in the list.
    """
    return sum(input_list)


# Elementwise reducers

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
   
    if isinstance(sequences[0], numpy.ndarray):
        m = numpy.matrix(sequences)
        res = m.min(0)
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

    return reduced_results

def mammy2(sequences, operation):
    """
    mapping and zipping like there's no tomorrow,
    but with special treatment for numpy arrays using matrices
    """
    
    if isinstance(sequences[0], numpy.ndarray):
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

    return reduced_results

def nummy(sequences, operation):
    """
    mapping and zipping like there's no tomorrow,
    but with special treatment for numpy arrays
    """
    if isinstance(sequences[0], numpy.ndarray):
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

def generate_data(size, participants, random=False, data_type=numpy.dtype('float64')):
    """
    Generate the dataset externally from measured functions so that impact is not measured

    size number of elements of type data_type are generated for each participant
    
    each participants sequence is unique 
    
    if random is applied the sequences are further randomized to avoid accidental caching effects
    otherwise so that elementwise operations that compare
    can't get off easily and correctness can be verified

    
    ISSUES:
    - no randomization yet
    - only works for string and numpy types for now
    """
    if size < participants:
        print "illegal parameters (size cannot be smaller than number of sequences)"
        return None
    
    wholeset = []
    
    # testdata repeats with a certain interval, if size is small relative to participants the interval is as long as the whole sequence
    if size > participants**2:
        interval = size/participants
    else:
        interval = size
    
    if data_type in (str,list,tuple):
        basestring = string.lowercase
        base = basestring
        # Ensure base is at least as large as interval
        while interval > len(base):
            base += basestring
        # Cut down to size
        base = base[:interval]
        
        for p in xrange(participants):            
            payload = base[:p]+'A'+base[p+1:] # Marker to distinguish sequences
            wholeset.append(payload*(size/interval))
        #print "interval:%i participants:%i sequence:%i " % (interval, participants, len(payload)*size/interval)
        
        if data_type == list:
            wholeset = map(list,wholeset)

        if data_type == tuple:
            wholeset = map(tuple,wholeset)
                
        
    elif isinstance(data_type,numpy.dtype):
        # ugly floats to use that precision
        #base = numpy.arange(0, interval, 1/3.0, dtype=numpy.float64,)
        base = numpy.arange(interval, dtype=data_type)
        for p in xrange(participants):
            payload = copy.copy(base)
            payload[p] = 42 # Marker to distinguish sequences
            wholeset.append( numpy.tile(payload,size/interval) )
        #print "interval:%i participants:%i sequence:%i " % (interval, participants, len(payload)*size/interval)
        
    else:
        print "unknown type"
        
    return wholeset

def runner(version=None):
    
    repetitions = 1000
    repetitions = 1
    
    participants = 4

    # Size definitions
    small = 10
    medium = 500
    large = 4000
    biglarge = 10000
    
    # What sizes to test
    sizes_to_test = [small,medium]
    sizes_to_test = [small]
    
    
    functions_to_test = [simple, xsimple, convoluted, zippy, mammy, mammy2, nummy]
    functions_to_test = [simple]
    
    types_to_test = [str, numpy.dtype('float64'), numpy.dtype('int32')]
    types_to_test = [numpy.dtype('float64'), numpy.dtype('int32')]
    types_to_test = [str, tuple, list]
    types_to_test = [tuple, list]
    
    
    operations_to_test = [max, min, all, any, sum]
    operations_to_test = [min,max]
    operations_to_test = [sum]
    
    
    for size in sizes_to_test:
        print "SIZE: %i" % size
        
        for t in types_to_test:
            print "\t%i of type: %s" % (size,t)
            
            test_data = generate_data(size, participants, False, t)
    
            for func in functions_to_test:
                for operation in operations_to_test:
                    #s = "size:%i, func:%s, type:%s, operation:%s %i repetitions" % (size, func.func_name, t, operation, repetitions)
                    s = "func:%s, operation:%s %i repetitions" % (func.func_name, operation, repetitions)
                    #print s
                    with timing(s, repetitions):
                        for r in xrange(repetitions):
                            
                            res = func(test_data,operation)
                            
                    print "VALIDATA:"
                    print res


runner()
