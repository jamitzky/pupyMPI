#!/bin/sh

PYTHONPATH=.    time -f "2 full: %E" bin/mpirun.py -c 2 tests/TEST_finalize_quickly.py 
PYTHONPATH=.    time -f "8 full: %E" bin/mpirun.py -c 8 tests/TEST_finalize_quickly.py 
PYTHONPATH=.    time -f "32 full: %E" bin/mpirun.py -c 32 tests/TEST_finalize_quickly.py 
PYTHONPATH=.    time -f "128 full: %E" bin/mpirun.py -c 128 tests/TEST_finalize_quickly.py
                 
PYTHONPATH=.    time -f "2 dyn: %E" bin/mpirun.py -c 2 tests/TEST_finalize_quickly.py --disable-full-network-startup
PYTHONPATH=.    time -f "8 dyn: %E"  bin/mpirun.py -c 8 tests/TEST_finalize_quickly.py --disable-full-network-startup
PYTHONPATH=.    time -f "32 dyn: %E"  bin/mpirun.py -c 32 tests/TEST_finalize_quickly.py --disable-full-network-startup
PYTHONPATH=.    time -f "128 dyn: %E"  bin/mpirun.py -c 128 tests/TEST_finalize_quickly.py --disable-full-network-startup