__all__ = ('AGGR_USER_CHOICES', 'find_function', 'DEFAULT_AGGR', )

def cust_avg(data_list):
    s = sum(data_list)
    c = len(data_list)
    
    if c:
        return s/c 
    
    return None

all_aggregates = {
    'min' : min,
    'max' : max,
    'sum' : sum,
    'avg' : cust_avg,
}

DEFAULT_AGGR = min

def find_function(aggr_name):
    try:
        return all_aggregates[aggr_name]
    except IndexError:
        return DEFAULT_AGGR
        
AGGR_USER_CHOICES = all_aggregates.keys()