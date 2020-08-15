import sys
import threading
import logging
import time
from txpool import *
from block_chain import *
from sorting import *
from transactions import *
from stopmine import StopMine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class NotError(Exception):
    pass


def packing():
    log.info("------into packing------")
    bc1 = BlockChain()
    tx_pool1 = TxPool()
    if len(tx_pool1.txs) == 0:
        log.info("oh no")
        return [], "no"
    total_fee = 0
    for tx1 in tx_pool1.txs:
        if tx1.amount <= 0.1:
            tx_pool1.txs.remove(tx1)
        if type(tx1) == 'dict':
            tx_pool1[tx_pool1.txs.index(tx1)] = Transaction.deserialize(tx1)
    selected_txs = []
    selected_tx = None
    log.info("------first for------")
    for tx1 in tx_pool1.txs:
        if selected_tx:
            if tx1.fee_size_ratio > selected_tx.fee_size_ratio and tx1.amount > 0.1:
                if tx1.verify():
                    selected_tx = tx1
        elif tx1.amount > 0.1 and tx1.verify():
            selected_tx = tx1
    if not selected_tx:
        log.info("oh no 2")
        return [], "no"
    selected_txs.append(selected_tx)
    total_fee += selected_tx.amount
    remain_txs = []
    log.info("selected")
    for i in tx_pool1.txs:
        if i.txid != selected_tx.txid and i.amount > 0.1:
            remain_txs.append(i)
    tx_pool1.txs = remain_txs
    log.info("------before return------")
    return selected_txs, total_fee


def finding_new_block():
    i = 1
    while i < 12:
        try:
            st = StopMine()
            st.mine_h = i
        except:
            pass
        bc1 = BlockChain()
        tx3, total_fee = packing()
        log.info("------return these information:" + str(tx3) + str(total_fee) + "------")
        try:
            if tx3:
                bc1.add_block(tx3, total_fee)
            elif total_fee == "no":
                log.info("no transaction left")
                bc1.add_block()
                log.info("mine a empty block")
            else:
                log.info("error in packing")
        except:
            log.info("------fall behind in mine------")
            try:
                st = StopMine()
                log.info("------with longest " + str(st.h) + " and local " + str(i) + "------")
                while i < st.h:
                    tx3, total_fee = packing()
                    i += 1
            except:
                pass
        i += 1
