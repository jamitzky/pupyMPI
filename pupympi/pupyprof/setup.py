#!/usr/bin/env python
# coding=utf8
from distutils.core import setup, Extension

setup(name="_pupyprof", 
	  version="0.1",
	  description="Profiler/tracefile generator for pupyMPI",
      author="Asser Schrøder Femø",
      author_email="asser@diku.dk",
	  ext_modules = [Extension
					 ("_pupyprof",
					  sources = ["_pupyprof.c", #"_ycallstack.c", 
					  #"_yhashtab.c", "_ymem.c", "_yfreelist.c", 
					  #"_ytiming.c"],
                      ],
					  #define_macros=[('DEBUG_MEM', '1'), ('DEBUG_CALL', '1'), ('YDEBUG', '1')],
					  #define_macros=[('YDEBUG', '1')],
					  #define_macros=[('DEBUG_CALL', '1')],
					  #define_macros=[('DEBUG_MEM', '1')],		
					  #extra_link_args = ["-lrt"]
					  #extra_compile_args = ["TEST"]
				     )
				    ],
	  py_modules =  ["pupyprof"]
)
