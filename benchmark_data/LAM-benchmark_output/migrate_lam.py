#!/usr/bin/env python

import re, sys, csv
from datetime import datetime

class State(object):
    def __init__(self):
        # The state variables
        self.test = ""
        self.procs = 0

        # Regular expressions to detect state change.
        self.test_re = re.compile(".*Benchmarking (\w+)")
        self.process_re = re.compile(".*#processes = (\d+)")

    def comment(self, line):
        test_match = self.test_re.match(line)
        process_match = self.process_re.match(line)

        if test_match:
            self.test = test_match.groups()[0]
        elif process_match:
            self.procs = int(process_match.groups()[0])

def parse_space_row(line):
    def type_predict(f):
        try:
            return int(f)
        except ValueError:
            try:
                return float(f)
            except ValueError:
                return f
    row = line.split(" ")

    # The row list contains a lot of empty elements, we can filter
    # with a standard python function.
    row = filter(None, row)

    # We don't trust the input. There can be newlines and other stuff in the
    # fields, so we strip each element.
    row = [s.strip() for s in row]

    # We try to predict the type of each element, so we can add 
    # float and ints without actually doing string concats. 
    row = [type_predict(f) for f in row]
    return row

if __name__ == "__main__":
    try:
        filename = sys.argv[1]
    except IndexError:
        print "You should call the script with the LAM file to migrate as the single element"
        sys.exit()

    reader = open(filename, "r")
    state = State()

    data_full = {}

    for line in reader:
        line = line.strip()
        if not line:
            continue

        row = parse_space_row(line)
        if line.startswith("#"):
            # We have found a comment... we test the comment for state change.
            state.comment(line)
        else:
            # We have cleared the row nicely now. If the row contains 4 or 5 elements
            # it's data and we can gather it.
            item = {'datasize' : 0, 'repititions' : 0, 'repititions' : 0,
                    't_user_sec' : 0, 'mbytes_sec' : 0, 't_min' : 0, 't_max' : 0, 
                    'test' : ""}

            if state.procs and state.procs not in data_full:
                data_full[state.procs ] = {}
           
            if len(row) == 4:
                # Skip head rows
                if type(row[0]) != int:
                    continue
                    
                item['datasize'] = row[0]
                item['repititions'] = row[1]
                item['t_user_sec'] = row[2]
                item['mbytes_sec'] = row[3]
                
                item['t_min'] = item['t_user_sec']
                item['t_max'] = item['t_user_sec']

                item['test'] = state.test

            elif len(row) == 5:
                item['datasize'] = row[0]
                item['repititions'] = row[1]

                item['t_min'] = row[2] 
                item['t_max'] = row[3]
                item['t_user_sec'] = row[4]
                item['mbytes_sec'] = None # FIXME: The datafile does not contain this data. 
                item['test'] = state.test
            elif len(row) == 6:
                item['datasize'] = row[0]
                item['repititions'] = row[1]

                item['t_min'] = row[2] 
                item['t_max'] = row[3]
                item['t_user_sec'] = row[4]
                item['mbytes_sec'] = row[5]
                item['test'] = state.test
            else:
                print "Soft warning. Found row with length", len(row)
                print "\t", row
                print line
                print ""
    
            # Finding the type of this test to match our benchmarking schema
            collectives = ['Allgather', 'Allreduce', 'Alltoall', 'Barrier', 'Bcast', 
                    'Gather', 'Reduce', 'Scatter',]
            single = [ 'PingPing', 'PingPong',]
            others = ['Allgatherv', 'Alltoallv', 'Exchange', 'Gatherv', 'Reduce_scatter',
                'Scatterv', 'Sendrecv',]

            # We actually discard the other types later, but for now we keep it in the
            # dict so we can always change the printing function to include it.
            test_type = None
            test = item['test']
            if test in collectives:
                test_type = "collective"
            elif test in single:
                test_type = "single"
            elif test in others:
                test_type = "other"
            else:
                print "Warning. Unknown test type for test", test

            if test_type not in data_full[state.procs]:
                data_full[state.procs][test_type] = {}

            if test not in data_full[state.procs][test_type]:
                data_full[state.procs][test_type][test] = []

            # Append the data to a large dict for later printing.
            data_full[state.procs][test_type][test].append(item)

    header_row = ['datasize','repetitions','total time','avg time/repetition',
            'min time/repetition','max time/repetition', 'Mb/second','nodes',
            'name of test','timestamp of testrun',]
    
    for procs in data_full.keys():
        procs_data = data_full[procs]
        for test_type in procs_data.keys():
            if test_type == "other":
                continue

            # Create file handle for this test
            filename = "MY_pupymark.%s.%dprocs.4MB.%s.csv" % (test_type[:4], procs, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
            fp = open(filename, "w")
            writer = csv.writer(fp)

            test_data = procs_data[test_type]

            for test in test_data.keys():
                writer.writerow(header_row)
                for rowd in test_data[test]:
                    row = [
                        rowd['datasize'], 
                        rowd['repititions'],
                        rowd['repititions']*rowd['t_user_sec'],
                        rowd['t_user_sec'],
                        rowd['t_min'],
                        rowd['t_max'],
                        rowd['mbytes_sec'],
                        procs,
                        test,
                        datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    ]
                    writer.writerow(row)
                fp.write("\r\n\r\n")
            fp.close()
