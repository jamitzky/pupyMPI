#!/usr/bin/env python

import datetime
import sys
import pylab
from pylab import figure, show, plot, ylim, yticks, arange, pi, sin, cos, sqrt
from numpy import arange
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

files = []
outfile = None

for arg in sys.argv[1:]:
    if arg == "--out":
        outfile = ""
    elif outfile == "":
        outfile = arg
    else:
        files.append(arg)


if files == [] or outfile == "":
    print "Usage: %s [--out <outfile.eps>] <file0> [file1] [file2] ..." % (sys.argv[0])
    sys.exit(-1)

if outfile != None and len(outfile) > 0:
    # Parameters for plotting to image
    fig_width_pt = 442.0  # Get this from LaTeX using \showthe\columnwidth
    inches_per_pt = 1.0/72.27               # Convert pt to inch
    golden_mean = (sqrt(5)-1.0)/2.0         # Aesthetic ratio
    fig_width = fig_width_pt*inches_per_pt  # width in inches
    fig_height = fig_width*golden_mean      # height in inches
    fig_size =  [fig_width,fig_height]
    params = {'backend': 'ps',
              'axes_labelsize': 10,
              'text.fontsize': 10,
              'legend.fontsize': 7,
              'xtick.labelsize': 8,
              'ytick.labelsize': 8,
              'xlabel.fontsize': 10,
              'font.family': 'Palatino',
              'text.usetex': True,
              'figure.figsize': fig_size}
    matplotlib.rcParams.update(params)

xs = []
ys = []
cs = []
rank = 0
state_colors = {
    'UNKNOWN'        : 'grey',
    'RUNNING'        : 'white',
    'MPI_WAIT'       : 'red',
    'MPI_COMM'       : 'blue',
    'MPI_COLLECTIVE' : 'orange',
    'FINALIZED'      : 'magenta',
}

for arg in files:
    try:
        f = open(arg, 'r')
    except IOError:
        print "Unable to open %s" % (arg)
        sys.exit(-1)

    lines = f.readlines()
    x = []
    y = []
    c = []

    for line in lines:
        if line.startswith("#"):
            continue

        (ts, _, state) = line.partition(" ")

        state = state.rstrip("\n")

        x.append(float(ts))
        y.append(int(rank))
        c.append(state_colors[state])

    xs.append(x)
    ys.append(y)
    cs.append(c)
    rank += 1

minx = min(min((xs[0])), min(xs[1]))

for i in range(0,len(xs)):
    xn = []
    cn = []
    for j in range(0,len(xs[i])):
        # Ignore the RUNNING states
        if cs[i][j] == state_colors["RUNNING"]:
            continue
        if j+1 < len(xs[i]):
            xn.append(((xs[i][j] - minx), xs[i][j+1] - xs[i][j]))
            cn.append(cs[i][j])
    xs[i] = xn
    cs[i] = cn

fig = plt.figure()
ax = fig.add_subplot(111)

rank = 0
for x in xs:
    ax.broken_barh(x, (rank*5+2.5, 5), facecolors=cs[rank], linewidth=0.0,
                   antialiased=False)
    rank += 1

ax.set_ylim(0, rank*5+5)
ax.set_xlabel('Seconds since start')
ax.set_yticks([x*5+5 for x in range(0,rank)])
ax.set_yticklabels(['P' + str(x) for x in range(0,rank)])

ps = []
for state in state_colors:
    p = Rectangle((0, 0), -1, -1, fc=state_colors[state])
    ps.append(p)
    ax.add_patch(p)

leg = fig.legend(tuple(ps), tuple(map(lambda x: x.replace("_", "\_"), state_colors.keys())))

for patch in leg.get_patches():
    patch.set_picker(5)

if outfile != None and len(outfile) > 0:
    plt.savefig(outfile)
else:
    plt.show()

