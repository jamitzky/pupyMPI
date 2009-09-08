#!/bin/sh
# hack: get the long one first, then the short one
pylint-2.6 --rcfile=pylint.semiverbose mpi/*
pylint-2.6 -e --rcfile=pylint.semiverbose mpi/*
