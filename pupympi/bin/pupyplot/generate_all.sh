#!/bin/sh

# Check if the file exists
if [ ! -e $1 ] 
then
	echo "No such file called $1"
	exit
fi

echo $1

rm -rf plots
mkdir plots

# Generate plots with x=datasize, y=time for all node counts
mkdir plots/datasize_time
for n in 2 4 8 16 32
do
	mkdir plots/datasize_time/$n
	python line.py --raw-filters=nodes:$n $1
	mv *.eps plots/datasize_time/$n/
done

# Generate plots wth x=nodes, y=time for selected data sizes
mkdir plots/nodes_time
for d in 4 64 1024 2048 32768 2097152 4194304
do
	mkdir plots/nodes_time/$d
	python line.py --raw-filters=datasize:$d $1
	mv *.eps plots/nodes_time/$d
done	

# Clean up if there are anything left from the runs
python cleanup.py
