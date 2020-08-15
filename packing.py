# packing function select a list txs = [...]
# until > 1MB or no tx
# verify if tx are valid
# return txs to be used in add_block(transactions)
# wait copy the verify function from other .py
# add info in start in cli.py : # log.info("mined a block")

"""
1. search in txpool : delete invalid transactions
2. sort the txpool
3. start add transactions into the list : until > 1MB or no tx
4. delete the packed transactions from the txpool
4. return the list of transactions (to be used in add_block)
"""

import sys
import threading
import logging
import time
from txpool import *
from block_chain import *
from sorting import *
from transactions import *
from stopmine import StopMine


logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class NotError(Exception):
    pass


def packing():
    log.info("------into packing------")
    bc1 = BlockChain()  # used to verify the transactions
    tx_pool1 = TxPool()
    total_fee = 0   # total fee 6.19
    for tx1 in tx_pool1.txs:    # 1. search in txpool : delete invalid transactions
        # if not bc1.verify_transaction(tx1):   # e1
            # raise NotError('valid')
            # tx_pool1.txs.remove(tx1)  # e1
            # raise NotError('invalid')
        if tx1.amount <= 0.1:   # e1
            tx_pool1.txs.remove(tx1)    # e1
        if type(tx1) == 'dict':
            tx_pool1[tx_pool1.txs.index(tx1)] = Transaction.deserialize(tx1)    # change 6.22
    # txs = sorting(tx_pool1.txs)    # 2. sort the txpool
    # log.info("------after sorting------")
    # log.info(txs)
    selected_txs = []
    if not tx_pool1.txs:
        return [], 0
    selected_tx = tx_pool1.txs[0]
    log.info("------first for------")
    for tx1 in tx_pool1.txs: # 3. start add transactions into the list : until > 1MB or no tx
        if tx1.fee_size_ratio > selected_tx.fee_size_ratio and tx1.amount > 0.1:
            selected_tx = tx1
        # selected_txs.append(tx1)
        # print(selected_txs[0].txid)
        # if sys.getsizeof(selected_txs) > 1048576:
            # raise NotError('bigger than 1 MB')
            # selected_txs.remove(tx1)
            # return selected_txs, total_fee  # change 6.20
        # else:
        #     remain_txs = []
        #     for i in tx_pool1.txs:
        #         if i.txid != tx1.txid:
        #             remain_txs.append(i)
        #     tx_pool1.txs = remain_txs    # 4. delete the packed transactions from the txpool
        #     # tx_pool1.txs.remove(tx1)   # there are some problems with his remove function --> not use it
        #     total_fee += tx1.amount    # add the fee
        # if selected_txs:
        #     log.info("------before return------")   # e1
    selected_txs.append(selected_tx)
    total_fee += selected_tx.amount
    remain_txs = []
    for i in tx_pool1.txs:
        if i.txid != selected_tx.txid and i.amount > 0.1:
            remain_txs.append(i)
    tx_pool1.txs = remain_txs
            # return selected_txs, total_fee  # e1
    log.info("------before return------")
    return selected_txs, total_fee  # change 6.20




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
                bc1.add_block(tx3, total_fee)    # wait try when there's no transaction
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

# def start_find():
#     t1 = threading.Thread(target=finding_new_block,args=()) # change
#     t1.start()  # change
