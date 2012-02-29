#!/usr/bin/env python

from distutils.core import setup

setup(
    name            = 'pupyMPI',
    version         = '0.9.7',
    description     = 'A generic 100% python MPI implementation.',
    author          = 'Frederik Hantho',
    author_email    = 'fred@yahoo.com',
    url             = 'https://bitbucket.org/bromer/pupympi',
    packages        = [
        'mpi',
        'mpi.collective', 'mpi.collective.request',
        'mpi.lib', 'mpi.lib.hostfile', 'mpi.lib.hostfile.mappers',
        'mpi.network',
        'mpi.topology'
    ],
    scripts = ['pympirun']
)

