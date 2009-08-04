import os
import logging, logging.handlers

def setup_log(filename, logname, debug, verbosity, quiet):
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
    return logger