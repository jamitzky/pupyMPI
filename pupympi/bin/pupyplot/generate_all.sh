#!/bin/sh

# Check if the file exists
if [ ! -e $1 ] 
then
	echo "No such file called $1"
	exit
fi

rm -rf plots
mkdir plots

echo "------------- Generating plots with datasize on x axis and time on y ------------"
# Generate plots with x=datasize, y=time for all node counts
mkdir plots/datasize_time
for n in 2 4 8 16 32
do
	mkdir plots/datasize_time/$n
	
	mkdir plots/datasize_time/$n/log
	python line.py --x-axis-use-data-points --axis-x-type=log --axis-y-type=log --test-filter=:pingping,:pingpong --raw-filters=nodes:$n $1
	mv *.eps plots/datasize_time/$n/log

	mkdir plots/datasize_time/$n/linlog
	python line.py --x-axis-use-data-points --axis-x-type=log --axis-y-type=lin --test-filter=:pingping,:pingpong --raw-filters=nodes:$n $1
	mv *.eps plots/datasize_time/$n/linlog

	mkdir plots/datasize_time/$n/lin
	python line.py --axis-y-type=lin $e --test-filter=:pingping,:pingpong --raw-filters=nodes:$n $1
	mv *.eps plots/datasize_time/$n/lin
done

# Plot the ping pong and ping ping test

echo "------------- Generating plots with nodes on x axis and time on y ------------"
python line.py --axis-y-type=log --test-filter=pingping,pingpong --raw-filters=nodes:2 $1
mv *.eps plots/datasize_time/2/log

python line.py --axis-y-type=lin --test-filter=pingping,pingpong --raw-filters=nodes:2 $1
mv *.eps plots/datasize_time/2/lin

python line.py  --x-axis-use-data-points --axis-y-type=lin --axis-x-type=log --test-filter=pingping,pingpong --raw-filters=nodes:2 $1
mv *.eps plots/datasize_time/2/linlog


# Generate plots wth x=nodes, y=time for selected data sizes
mkdir plots/nodes_time
for d in 4 64 1024 2048 32768 2097152 4194304
do
	mkdir plots/nodes_time/$d

	mkdir plots/nodes_time/$d/log
	python line.py --raw-filters=datasize:$d --test-filter=:barrier,:pingping,:pingpong --axis-y-type=log --axis-x-type=lin --x-axis-use-data-points  --series-column=none --x-data=nodes $1
	mv *.eps plots/nodes_time/$d/log

	mkdir plots/nodes_time/$d/lin
	python line.py --raw-filters=datasize:$d --test-filter=:barrier,:pingping,:pingpong --axis-y-type=lin --axis-x-type=lin --x-axis-use-data-points  --series-column=none --x-data=nodes $1
	mv *.eps plots/nodes_time/$d/lin

	mkdir plots/nodes_time/$d/linlog
	python line.py --raw-filters=datasize:$d --test-filter=:barrier,:pingping,:pingpong --axis-y-type=lin --axis-x-type=log --x-axis-use-data-points  --series-column=none --x-data=nodes $1
	mv *.eps plots/nodes_time/$d/linlog
	
	
done	

# Handle barrier manually.
mkdir plots/nodes_time/barrier/

python line.py --test-filter=barrier --axis-y-type=lin --axis-x-type=lin  --x-axis-use-data-points --series-column=none --x-data=nodes $1
mv Barrier.eps plots/nodes_time/barrier/lin.eps

python line.py --test-filter=barrier --axis-y-type=lin --axis-x-type=log  --x-axis-use-data-points --series-column=none --x-data=nodes $1
mv Barrier.eps plots/nodes_time/barrier/linlog.eps

python line.py --test-filter=barrier --axis-y-type=log --axis-x-type=log  --x-axis-use-data-points --series-column=none --x-data=nodes $1
mv Barrier.eps plots/nodes_time/barrier/log.eps


# Clean up if there are anything left from the runs
python cleanup.py
