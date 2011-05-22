import yappi
yappi.start(True)
f = open("foo", "w")
f.write("bar")
f.close()
yappi.stop()
stats = yappi.get_stats(yappi.SORTTYPE_NAME)
for stat in stats: print stat
