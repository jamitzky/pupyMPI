import os
import logging, logging.handlers

class Logger:

    __shared_state = {}
    def __init__(self, *args, **kwargs):
        self.__dict__ = self.__shared_state 

        if not "_logger_instance" in self.__dict__:
            self.setup_log(*args, **kwargs)
        
    def setup_log(self, filename, logname, debug, verbosity, quiet):
        # FIXME: There is something wrong with the logger. Without options
        # errors is not in the file or stderr. It should. 
        if debug:
            verbosity = 3
            
        verbosity_conversion = [logging.ERROR,logging.WARNING,logging.INFO,logging.DEBUG]
        
        level = verbosity_conversion[ verbosity ]
        _BASE = os.path.dirname(os.path.abspath(__file__))
        _LOG_BASE = os.path.join(_BASE, '..', '%s.log')
        filepath = _LOG_BASE % os.path.basename(filename)
        basename = os.path.splitext(os.path.basename(filename))[0]
        
        filelog = logging.FileHandler(filepath)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
        filelog.setFormatter(formatter)
        filelog.setLevel(level)
        logging.getLogger(logname).addHandler(filelog)
       
        if not quiet and verbosity > 0:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(level)
            logging.getLogger(logname).addHandler(console)

        logger = logging.getLogger(logname)
        logger.setLevel(level)
        self.__dict__['_logger_instance'] = logger
        self.logger = logger

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
