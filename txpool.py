# coding:utf-8
from utils import Singleton

class TxPool(Singleton):    # only one in whole node
    SIZE = 1    # change to 0 : will be useless
    def __init__(self):
        if not hasattr(self, "txs"):
            self.txs = []
        if not hasattr(self, "pre_txs"):    # 7.20
            self.pre_txs = []   # 7.20

    def is_full(self):  # change : will be useless
        return len(self.txs) >= self.SIZE   # change : will be useless

    def add(self, tx):
        is_new = True
        for id in self.pre_txs:
            if id == tx.txid:
                is_new = False
                break
        if is_new:
            self.txs.append(tx)
            self.pre_txs.append(tx.txid)    # 7.20

    def clear(self):
        self.txs.clear()

    def is_new(self, tx):   # 7.20
        return not tx.txid in self.pre_txs  # 7.20
