
def error_handling(f):
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            print "The error handler got an exception to handle"
            print e
    return inner
            
