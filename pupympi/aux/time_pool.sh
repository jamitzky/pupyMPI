#!/bin/sh

time PYTHONPATH=. bin/mpirun.py -c 2 tests/TEST_finalize_quickly.py 
time PYTHONPATH=. bin/mpirun.py -c 8 tests/TEST_finalize_quickly.py 
time PYTHONPATH=. bin/mpirun.py -c 32 tests/TEST_finalize_quickly.py 
time PYTHONPATH=. bin/mpirun.py -c 128 tests/TEST_finalize_quickly.py

time PYTHONPATH=. bin/mpirun.py -c 2 tests/TEST_finalize_quickly.py --disable-full-network-startup
time PYTHONPATH=. bin/mpirun.py -c 8 tests/TEST_finalize_quickly.py --disable-full-network-startup
time PYTHONPATH=. bin/mpirun.py -c 32 tests/TEST_finalize_quickly.py --disable-full-network-startup
time PYTHONPATH=. bin/mpirun.py -c 128 tests/TEST_finalize_quickly.py --disable-full-network-startup