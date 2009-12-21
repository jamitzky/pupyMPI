#!/bin/sh


# badpuppy.sh
#
# Kill script to for easy cleaning of hanging pupympi procs no the cluster
#
# Created by Jan Wiberg on 2009-08-06.
# Copyright (c) 2009 __MyCompanyName__. All rights reserved.

killall -u fhantho python2.6
ssh n0 killall -u fhantho python2.6
ssh n1 killall -u fhantho python2.6
ssh n2 killall -u fhantho python2.6
ssh n3 killall -u fhantho python2.6
ssh n4 killall -u fhantho python2.6
ssh n5 killall -u fhantho python2.6
ssh n6 killall -u fhantho python2.6
ssh n7 killall -u fhantho python2.6