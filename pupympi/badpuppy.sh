#!/bin/sh


# badpuppy.sh
#
# Kill all runaway python processes on all nodes

ssh n0 killall python2.6
ssh n1 killall python2.6
ssh n2 killall python2.6
ssh n3 killall python2.6
ssh n4 killall python2.6
ssh n5 killall python2.6
ssh n6 killall python2.6
ssh n7 killall python2.6

