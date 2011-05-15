#!/bin/sh

# Check if the file exists
if [ ! -e $1 ] 
then
	echo "No such file called $1"
	exit
fi

rm -rf plots
mkdir plots

# Generate plots with x=datasize, y=time for all node counts
mkdir plots/datasize_time
for n in 2 4 8 16 32
do
	mkdir plots/datasize_time/$n
	for t in "log" "lin"
	do
		mkdir plots/datasize_time/$n/$t
		python line.py --axis-y-type=$t --raw-filters=nodes:$n $1
	    if [ $? -eq 0 ]; then
			mv *.eps plots/datasize_time/$n/$t
		else
			echo "Prolem with the following plot command"
			echo "python line.py --axis-y-type=$t --raw-filters=nodes:$n $1"
		fi
	done
done

# Generate plots wth x=nodes, y=time for selected data sizes
mkdir plots/nodes_time
for d in 4 64 1024 2048 32768 2097152 4194304
do
	mkdir plots/nodes_time/$d
	for t in "log" "lin"
	do
		mkdir plots/nodes_time/$d/$t
		python line.py --raw-filters=datasize:$d --axis-y-type=$t --x-data=nodes $1
		if [ $? -eq 0 ]; then
			mv *.eps plots/nodes_time/$d/$t
		else
			echo "Prolem with the following plot command"
			echo "python line.py --raw-filters=datasize:$d --axis-y-type=$t --x-data=nodes $1"
		
		fi
	done
done	

# Clean up if there are anything left from the runs
python cleanup.py
