#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import logging, logging.handlers

class Logger:

    __shared_state = {} # Shared across all instances
    # singleton check
    def __init__(self, *args, **kwargs):
        self.__dict__ = self.__shared_state 

        if not "_logger_instance" in self.__dict__:
            self.setup_log(*args, **kwargs)
    """
    parameters:
    quiet: supresses output to console
    debug: Well this parameter is just silly
    verbosity: Set level of incident generating log entries
    """    
    def setup_log(self, filename, logname, debug, verbosity, quiet):
        if debug or (verbosity > 3):
            verbosity = 3
        
        # Conversion to pythonic logging levels
        verbosity_conversion = [logging.ERROR,logging.WARNING,logging.INFO,logging.DEBUG]        
        level = verbosity_conversion[ verbosity ]
        
        # Decide where to put and what to call the logfile 
        _BASE = os.path.dirname(os.path.abspath(__file__))
        _LOG_BASE = os.path.join(_BASE, '..', '%s.log')
        filepath = _LOG_BASE % os.path.basename(filename)
        basename = os.path.splitext(os.path.basename(filename))[0]
        
        filelog = logging.FileHandler(filepath)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
        filelog.setFormatter(formatter)
        filelog.setLevel(level)
        logging.getLogger(logname).addHandler(filelog)
        
        # Add a handler to do std out logging if verbosity demands it and quiet is not on
        if not quiet and verbosity > 0:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(level)
            logging.getLogger(logname).addHandler(console)

        logger = logging.getLogger(logname)
        logger.setLevel(level)
        self.__dict__['_logger_instance'] = logger
        #self.logger = logger # believed to be superflous

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        if attr not in ("logger", ):
            return setattr(self.logger, attr, value)

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        if attr == "logger":
            return self.__dict__['_logger_instance']
        else: 
            logger = self.__dict__['_logger_instance']
            return getattr(logger, attr)
