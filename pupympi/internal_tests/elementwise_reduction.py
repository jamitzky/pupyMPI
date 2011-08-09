"""
Testing various ways to apply an operation elementwise on a collection of sequences
Sequences can be everything iterable

ISSUES:
Need validation mode
Bool type is out for now
The numpy average function is not used since it is not ufunc and also needs an axis argument or it will flatten sequences

TESTING NOTES:
sum vs. MPI_sum for types that sum can deal with
sum vs. math.fsum? or just use numpy when summing floats?
sum vs. max vs min vs. avg for relevant types


"""
import sys, csv, string, copy, time, math, numpy
from contextlib import contextmanager

sys.path.append('..') # include parent dir in PYTHONPATH so we can import operations without further trickery
from mpi.collective import operations

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
            print "%s%f;%f" % (printstr, total_time, avg_time)
        else:
            print "%s%f sec." % (printstr, total_time)


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
    if isinstance(sequences[0],numpy.ndarray):
        reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
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
    if isinstance(sequences[0],numpy.ndarray):
        reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
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
    if isinstance(sequences[0],numpy.ndarray):
        reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
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
    if isinstance(sequences[0],numpy.ndarray):
        reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
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

    numpy_matrix_op = getattr(operation, "numpy_matrix_op", None)

    if isinstance(sequences[0], numpy.ndarray) and numpy_matrix_op:
        # Find the proper matrix operation as defined in operations.py
        # or hope that the built-in Python operation has a corresponding matrix operation with same name
        # Make a matrix
        m = numpy.matrix(sequences)
        # Find the resultmatrix
        res = getattr(m, numpy_matrix_op)(0)
        # Get one-dimensional array from result matrix
        reduced_results = res.A[0]
    else:
        reduced_results = map(operation,zip(*sequences))

    # Restore the type of the sequence
    if isinstance(sequences[0],numpy.ndarray):
        reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
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
    numpy_op = getattr(operation, "numpy_op", None)

    if isinstance(sequences[0], numpy.ndarray) and numpy_op:
        reduced_results = numpy_op(sequences)
    else:
        reduced_results = map(operation,zip(*sequences))

        # Restore the type of the sequence
        if isinstance(sequences[0],numpy.ndarray):
            reduced_results = numpy.array(reduced_results,dtype=sequences[0].dtype)
        if isinstance(sequences[0],str):
            reduced_results = ''.join(reduced_results) # join char list into string
        if isinstance(sequences[0],bytearray):
            reduced_results = bytearray(reduced_results) # make byte list into bytearray
        if isinstance(sequences[0],tuple):
            reduced_results = tuple(reduced_results) # join

    return reduced_results

#def mappy(sequences, operation):
#    """
#    NOTE: Mappy has been retired since it doesn't currently work
#    mapping and zipping like there's no tomorrow
#    """
#    reduced_results = map(operation,*sequences)
#
#    # Restore the type of the sequence
#    if isinstance(sequences[0],str):
#        reduced_results = ''.join(reduced_results) # join char list into string
#    if isinstance(sequences[0],bytearray):
#        reduced_results = bytearray(reduced_results) # make byte list into bytearray
#    if isinstance(sequences[0],tuple):
#        reduced_results = tuple(reduced_results) # join
#
#    return reduced_results

def generate_data(size, participants, random=False, data_type=numpy.dtype('float64')):
    """
    Generate the dataset externally from measured functions so that impact is not measured

    size number of elements of type data_type are generated for each participant

    each participants sequence is unique

    if random is applied the sequences are further randomized to avoid accidental caching effects
    otherwise so that elementwise operations that compare
    can't get off easily and correctness can be verified


    ISSUES:
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
        print "Error: unknown type!"

    return wholeset


def validator(only_numpy=False):
    """
    Test that all functions agree on results
    """
    size = 5
    participants = 4

    # Numpy types
    ntypes = [numpy.dtype('float64'), numpy.dtype('float32'), numpy.dtype('int64'), numpy.dtype('int32'), numpy.dtype('uint16')]

    # Python types
    ptypes = [str, list ,tuple]

    # String in-capable operations
    nostring = [sum, all, any, operations.MPI_prod, operations.MPI_avg]

    # String capable operations
    stringy = [operations.MPI_sum, operations.MPI_max, operations.MPI_min, max, min]

    # reducing functions
    functions_to_test = [simple, xsimple, convoluted, zippy, mammy, nummy]
    functions_to_test = [nummy,mammy]
    functions_to_test = [mammy]

    if only_numpy:
        # Without strings etc. - ie. only numpy types
        types_to_test = ntypes
        #operations_to_test = [operations.MPI_avg]
        operations_to_test = nostring + stringy
    else:
        # With strings etc.
        types_to_test = ntypes + ptypes
        operations_to_test = stringy


    for t in types_to_test:
        test_data = generate_data(size,participants, False, t)
        print "TESTDATA:%s type:%s specified type:%s" % (test_data, type(test_data[0]),t)
        #print "TESTDATA:%s type:%s specified type:%s" % (test_data, type(test_data[0][0]),t)

        for operation in operations_to_test:
            results = []
            for func in functions_to_test:
                res = func(test_data, operation)
                results.append(res)
                s = "result:%s - from func:%s, type:%s operation:%s" % (res, func.func_name, type(res), operation)
                print s

                # Validate that types match
                try:
                    assert str(res.dtype) == t
                except AttributeError, e: # non-numpy types do not have dtype attribute
                    assert type(res) == t
                except AssertionError, e:
                    # Avg operation goes from int to float and is specifically whitelisted here
                    if operation == operations.MPI_avg:
                        #print "Info: avg initial type:%s not equal to result type:%s" % (t, str(res.dtype))
                        pass
                    else:
                        print "Error: initial type:%s not equal to result type:%s" % (t, str(res.dtype))
                        raise e

            # Validate that all elements of the list are the same
            if operation == operations.MPI_avg:
                # Avg operation goes from int to float and is specifically whitelisted here
                print
                pass
            else:
                try:
                    assert numpy.array_equal(results[1:],results[:-1])
                except AttributeError, e: # non-numpy types does not work with array_equal
                    assert results.count(results[0]) == len(results)
                except AssertionError, e:
                    print "Error: operation:%s function%s" % (operation, func)
                    raise e


def runner():

    try:
        repetitions = int(sys.argv[1])
    except:
        repetitions = 100

    participants = 3

    # Size definitions
    small = 10
    medium = 500
    large = 4000
    biglarge = 10000

    # What sizes to test
    #sizes_to_test = [small,medium]
    #sizes_to_test = [small]
    sizes_to_test = [medium,large]


    #functions_to_test = [simple, xsimple, convoluted, zippy, mammy, nummy]
    #functions_to_test = [simple]
    #functions_to_test = [zippy, mammy, nummy] # Fast ones only
    functions_to_test = [simple, xsimple, convoluted, zippy, mammy, nummy] # all of them

    #types_to_test = [str, numpy.dtype('float64'), numpy.dtype('int32')]
    #types_to_test = [str, tuple, list]
    types_to_test = [numpy.dtype('float64'), numpy.dtype('float32'), numpy.dtype('int64'), numpy.dtype('int32')]

    #operations_to_test = [max, min, all, any, sum] # built-ins
    operations_to_test = [sum, operations.MPI_sum, max, operations.MPI_max, min, operations.MPI_min, operations.MPI_avg]
    #operations_to_test = [sum, operations.MPI_sum, operations.MPI_avg, operations.MPI_min]

    for size in sizes_to_test:
        for t in types_to_test:
            test_data = generate_data(size, participants, False, t)

            for operation in operations_to_test:
                try:
                    opname = operation.func_name
                except AttributeError as e:
                    opname = "built-in %s" % str(operation)[-4:-1] # all the built-in ops are three letter
                for func in functions_to_test:
                    #s = "size:%i, func:%s, type:%s, operation:%s %i repetitions" % (size, func.func_name, t, operation, repetitions)
                    s = "size:%d;type:%s;func:%s;operation:%s;repetitions:%d;" % (size,t,str(func.func_name), opname, repetitions)
                    #print s
                    with timing(s, repetitions):
                        for r in xrange(repetitions):
                            res = func(test_data,operation)

if __name__ == "__main__":
    runner()
