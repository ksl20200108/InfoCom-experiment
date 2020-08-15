import operator
from transactions import *
from txpool import *

def sorting(txs):
    cmpfun = operator.attrgetter('fee_size_ratio')
    txs.sort(key=cmpfun)
    txs.reverse()
    return txs
