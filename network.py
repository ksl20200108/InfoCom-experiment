import threading
import time
import logging
import asyncio
import socket
import json
import random
import struct
import fcntl
import os

from kademlia.network import Server
from block_chain import BlockChain
from block import Block
from txpool import TxPool
from transactions import Transaction
from utils import Singleton
from conf import bootstrap_host, bootstrap_port, listen_port
from stopmine import StopMine
from utxo import *

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


class P2p(object):
    def __init__(self):
        self.server = Server()
        self.loop = None

    def run(self):
        loop = asyncio.get_event_loop()
        self.loop = loop
        loop.run_until_complete(self.server.listen(listen_port))
        self.loop.run_until_complete(self.server.bootstrap(
            [(bootstrap_host, bootstrap_port)]))
        loop.run_forever()

    def get_nodes(self):
        log.info("------------")
        nodes = []
        if self.server.protocol:
            for bucket in self.server.protocol.router.buckets:
                nodes.extend(bucket.get_nodes())
        return nodes


class Msg(object):
    NONE_MSG = 0
    HAND_SHAKE_MSG = 1
    GET_BLOCK_MSG = 2
    TRANSACTION_MSG = 3
    SYNCHRONIZE_MSG = 4
    MISS_TRANSACTION_MSG = 5
    GET_TRANSACTION_MSG = 6

    def __init__(self, code, data):
        self.code = code
        self.data = data


class TCPServer(object):
    def __init__(self, ip='0.0.0.0', port=listen_port):
        self.sock = socket.socket()
        self.ip = ip
        self.port = port

    def listen(self):
        self.sock.bind((self.ip, self.port))
        self.sock.listen(125)

    def run(self):
        t = threading.Thread(target=self.listen_loop, args=())
        t.start()

    def handle_loop(self, conn, addr):
        while True:
            log.info("------s handle loop------")
            header_size = struct.unpack('i', conn.recv(4))[0]
            header_bytes = conn.recv(header_size)
            header = eval(header_bytes.decode())
            send_size = header["send_size"]
            recv_size = 0
            recv_data = b''
            while recv_size < send_size:
                res = conn.recv(1024)
                recv_data += res
                recv_size += len(res)
            log.info("------server handle_loop recv_data:" +
                     str(recv_data)[1:] + "------")
            if not recv_data:
                log.info("------server handle_loop connection broke------")
                return
            try:
                try:
                    recv_msg = eval(recv_data.decode())
                except:
                    log.info("------server the null data is" +
                             str(recv_data) + "------")

                log.info("------server handle loop receive------")
                send_data = self.handle(recv_msg, conn, addr)
                log.info("tcpserver_send:" + send_data)
                log.info("------data send to: " + str(addr) + "------")
                send_bytes = send_data.encode()
                header_json = json.dumps({"send_size": len(send_bytes)})
                header_bytes = header_json.encode()
                header_size = len(header_bytes)
                time.sleep(2)
                conn.sendall(struct.pack('i', header_size))
                conn.sendall(header_bytes)
                conn.sendall(send_bytes)
            except:
                send_data = json.dumps(Msg(Msg.NONE_MSG, "").__dict__)
                send_bytes = send_data.encode()
                header_json = json.dumps({"send_size": len(send_bytes)})
                header_bytes = header_json.encode()
                header_size = len(header_bytes)
                time.sleep(2)
                conn.sendall(struct.pack('i', header_size))
                conn.sendall(header_bytes)
                conn.sendall(send_bytes)
                log.info("------receive Unsuccessfully------")

    def listen_loop(self):
        while True:
            conn, addr = self.sock.accept()
            log.info("--------conn: " + str(conn) +
                     "addr: " + str(addr) + "--------------")
            t = threading.Thread(target=self.handle_loop, args=(conn, addr))
            t.start()

    def handle(self, msg, conn, addr):
        code = msg.get("code", 0)
        log.info("code:" + str(code))
        if code == Msg.HAND_SHAKE_MSG:
            log.info("------server receive HAND_SHAKE_MSG------")
            res_msg = self.handle_handshake(msg, conn, addr)
        elif code == Msg.GET_BLOCK_MSG:
            log.info("------server receive GET_BLOCK_MSG------")
            res_msg = self.handle_get_block(msg, conn, addr)
        elif code == Msg.TRANSACTION_MSG:
            log.info("------server receive TRANSACTION_MSG------")
            res_msg = self.handle_transaction(msg, conn, addr)
        elif code == Msg.SYNCHRONIZE_MSG:
            log.info("------server receive SYNCHRONIZE_MSG------")
            res_msg = self.handle_synchronize(msg, conn, addr)
        elif code == Msg.MISS_TRANSACTION_MSG:
            log.info("------server receive MISS_TRANSACTION_MSG------")
            res_msg = self.handle_miss(msg, conn, addr)
        else:
            time.sleep(1)
            return json.dumps(Msg(Msg.NONE_MSG, "").__dict__)

        if res_msg:
            time.sleep(1)
            return json.dumps(res_msg.__dict__)
        else:
            time.sleep(1)
            return json.dumps(Msg(Msg.NONE_MSG, "").__dict__)

    def handle_handshake(self, msg, conn, addr):
        log.info("------server handle_handshake from " +
                 str(addr) + "------")
        data = msg.get("data", "")
        last_height = data.get("last_height", 0)
        log.info("------with last_height " + str(last_height) + "------")
        block_chain = BlockChain()
        block = block_chain.get_last_block()
        log.info('------s hand_shake ls_blo ' + str(block) + '------')

        if block:
            local_last_height = block.block_header.height
        else:
            local_last_height = -1
        log.info("server local_last_height %d, last_height %d" %
                 (local_last_height, last_height))

        if local_last_height >= last_height:
            try:
                st = StopMine()
                log.info('------works------')
                if st.h < local_last_height:
                    st.h = local_last_height
                    log.info("------" + str(addr) + " is the highest " + str(st.h) + "------")
            except:
                log.info('------dont work------')
            log.info("------server handle_handshake precede------")
            try:
                genesis_block = block_chain[0]
            except:
                genesis_block = None
            data = {
                "last_height": -1,
                "genesis_block": ""
            }
            if genesis_block:
                data = {
                    "last_height": local_last_height,
                    "genesis_block": genesis_block.serialize()
                }
            msg = Msg(Msg.HAND_SHAKE_MSG, data)
            return msg

        elif local_last_height < last_height:
            try:
                st = StopMine()
                if st.h < last_height:
                    st.h = last_height
                    st.ip = addr
                    log.info('------works------')
                    log.info("------" + str(addr) + ' is the highest ' + str(st.h) + "------")
            except:
                log.info('failed to stop mine')
            log.info("------server handle_handshake fall behind------")
            start_height = 0 if local_last_height == -1 else local_last_height
            synchronize_range = [start_height + 1, last_height + 1]
            log.info("------server need synchronize range " +
                     str(synchronize_range[0]) + " " + str(synchronize_range[1]) + "------")
            send_msg = Msg(Msg.SYNCHRONIZE_MSG, synchronize_range)
            return send_msg

    def handle_get_block(self, msg, conn, addr):
        log.info("------server handle_get_block from " +
                 str(addr) + "------")
        get_range = msg.get("data", 1)
        log.info("------with range " +
                 str(get_range[0]) + " " + str(get_range[1]) + "------")
        block_chain = BlockChain()
        data = []
        for height in range(1, get_range[1]):
            block = None
            while not block:
                try:
                    block = block_chain.get_block_by_height(height)
                    time.sleep(2)
                except:
                    time.sleep(2)
            data.append(block.serialize())
        msg = Msg(Msg.GET_BLOCK_MSG, data)
        log.info("------server send get_block msg" +
                 str(data) + "------")
        return msg

    def handle_transaction(self, msg, conn, addr):
        log.info("------server handle_transaction------")
        tx_pool = TxPool()
        txs = msg.get("data", {})
        for tx_data in txs:
            log.info("------server handle_transaction: for------")
            tx = Transaction.deserialize(tx_data)
            is_new = True
            if tx_pool.is_new(tx):
                log.info("------server never get this transaction before------")
                bc = BlockChain()
                ls_bl = bc.get_last_block()
                log.info('------s handle_tran ls_blo ' + str(ls_bl) + '------')
                if ls_bl:
                    ls_height = ls_bl.block_header.height
                    for i in range(0, ls_height + 1):
                        while True:
                            block = None
                            try:
                                block = bc.get_block_by_height(i)
                            except:
                                continue
                            if block:
                                break
                        bc_txs = block._transactions
                        if bc_txs:
                            for transaction in bc_txs:
                                if transaction.txid == tx.txid:
                                    log.info("------old transaction------")
                                    log.info("------the id is: " +
                                             str(tx.txid) + "------")
                                    is_new = False
                                else:
                                    log.info("------brand new------")
                                    log.info("------the id is: " +
                                             str(tx.txid) + "------")
                        if not is_new:
                            break
                if is_new:
                    tx_pool.add(tx)
                    log.info("------server add this transaction------")
                    log.info("------the id is: " + str(tx.txid) + "------")
                    server1 = PeerServer()
                    server1.broadcast_tx(tx)
                    log.info("------server handle_transaction broadcast------")
        msg = Msg(Msg.NONE_MSG, "")
        return msg

    def handle_synchronize(self, msg, conn, addr):
        datas = msg.get("data", "")
        log.info("------s handle_synchronize from " + str(addr) + "------")
        log.info("------with data " + str(datas) + "------")
        bc = BlockChain()
        try:
            st = StopMine()
            log.info('------works------')
            if st.ip != addr and st.ip:
                log.info('not ip ' + str(st.ip) + '------')
                return Msg(Msg.NONE_MSG, "")
            log.info('------is the highest ' + str(st.ip) + "------")
        except:
            return Msg(Msg.NONE_MSG, "")
        try:
            last_block = None
            while not last_block:
                last_block = bc.get_last_block()
                time.sleep(1)
            last_height = last_block.block_header.height
            for i in range(len(datas)-1, -1, -1):
                block = Block.deserialize(datas[i])
                log.info("roll back others' block at " + str(i) + str(block))
                if block.block_header.height > last_height:
                    last_height -= 1
                    continue
                elif block.block_header.height == last_height:
                    last_height -= 1
                    local_block = None
                    while not local_block:
                        local_block = bc.get_block_by_height(block.block_header.height)
                        time.sleep(1)
                    if local_block != block:
                        log.info("not the same ")
                        log.info("local" + str(local_block))
                        log.info("block " + str(block))
                        utxo_set = UTXOSet()
                        utxo.roll_back(local_block)
                        bc.roll_back()
                    else:
                        log.info("the same at " + str(local_block.block_header.height))
                        break
                else:
                    log.info("local >> " + str(last_block.block_header.height))
                    msg = Msg(Msg.NONE_MSG, "")
                    return msg
            last_height = last_block.block_header.height
            for data in datas:
                block = Block.deserialize(data)
                if block.block_header.height <= last_height:
                    continue
                elif block.block_header.height == last_height + 1:
                    last_height += 1
                    bc.add_block_from_peers(block, last_block)
                    log.info("s add block from peers " + str(block))
                    last_block = block
            msg = Msg(Msg.NONE_MSG, "")
            return msg
        except:
            log.info("------server handle_get_block failed get last block------")
            msg = Msg(Msg.NONE_MSG, "")
            return msg

    def handle_miss(self, msg, conn, addr):
        log.info("------server handle miss------")
        data = msg.get("data", "")
        tx_pool1 = TxPool()
        log.info("------server tx: " + str(len(tx_pool1.pre_txs)) +
                 "client tx: " + str(int(data)) + "------")
        if len(tx_pool1.pre_txs) <= int(data) and len(tx_pool1.pre_txs) < 11:
            log.info("------shorter------")
            msg = Msg(Msg.GET_TRANSACTION_MSG, "")
            return msg
        elif int(data) > len(tx_pool1.pre_txs):
            log.info("------longer------")
            data = [tx.serialize() for tx in tx_pool1.txs]
            msg = Msg(Msg.MISS_TRANSACTION_MSG, data)
            return msg
        else:
            log.info("------the same------")
            msg = Msg(Msg.NONE_MSG, "")
            return msg


class TCPClient(object):
    def __init__(self, ip, port):
        self.txs = []
        self.sock = socket.socket()
        self.ip = ip
        self.port = port
        log.info("connect ip:" + ip + "\tport:" + str(port))
        self.sock.connect((ip, port))
        self.time = time.time()

    def add_tx(self, tx):
        log.info("------client add_tx------")
        self.txs.append(tx)

    def send(self, msg):
        log.info("------client send------")
        try:
            data = json.dumps(msg.__dict__)
            send_bytes = data.encode()
            header_json = json.dumps({"send_size": len(send_bytes)})
            header_bytes = header_json.encode()
            header_size = len(header_bytes)
            time.sleep(3)
            self.sock.sendall(struct.pack('i', header_size))
            self.sock.sendall(header_bytes)
            self.sock.sendall(send_bytes)
            log.info("client send to:" + self.ip + "------with these data" + data)
        except:
            p_s = PeerServer()
            p_s.ips.remove(self.ip)
            return
        try:
            header_size = struct.unpack('i', self.sock.recv(4))[0]
            header_bytes = self.sock.recv(header_size)
            header = eval(header_bytes.decode())
            send_size = header["send_size"]
            recv_size = 0
            recv_data = b''
            while recv_size < send_size:
                res = self.sock.recv(1024)
                recv_data += res
                recv_size += len(res)
            log.info("client_recv_data from:" + self.ip +
                     "------with these data" + str(recv_data))
        except:
            log.info("c recv wrongly " + str(recv_data))
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()
            # self.shake_loop()
        try:
            log.info("------client try loads and handle data------")
            recv_msg = eval(recv_data.decode())
            self.handle(recv_msg)
            log.info("------client had loads and handle data------")
        except:
            log.info("c eval wrongly " + str(recv_data))
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()
            # self.shake_loop()

    def handle(self, msg):
        code = msg.get("code", 0)
        log.info("client handle: recv code:" + str(code))
        if code == Msg.HAND_SHAKE_MSG:
            self.handle_shake(msg)
        elif code == Msg.GET_BLOCK_MSG:
            self.handle_get_block(msg)
        elif code == Msg.TRANSACTION_MSG:
            self.handle_transaction(msg)
        elif code == Msg.SYNCHRONIZE_MSG:
            self.handle_synchronize(msg)
        elif code == Msg.GET_TRANSACTION_MSG:
            self.handle_get_transaction(msg)
        elif code == Msg.MISS_TRANSACTION_MSG:
            self.handle_miss(msg)
        else:
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()
            # self.shake_loop()

    def shake_loop(self):
        time.sleep(3)
        log.info("------c shake_loop ip:" + self.ip +
                 "\tport:" + str(self.port) + "------")
        tx_pool1 = TxPool()
        if self.txs:
            log.info("------c has txs------")
            data = [tx.serialize() for tx in self.txs]
            self.txs = []
            log.info("------c serialize transaction-------")
            msg = Msg(Msg.TRANSACTION_MSG, data)
            self.send(msg)
        elif tx_pool1.pre_txs:
            a = random.uniform(0, 1)
            if a < 0.7 and (time.time() - self.time) < 30:
                log.info("------has previous transaction------")
                data = len(tx_pool1.pre_txs)
                msg = Msg(Msg.MISS_TRANSACTION_MSG, data)
                self.send(msg)
            else:
                log.info("shake")
                block_chain = BlockChain()
                block = block_chain.get_last_block()
                log.info('------c s_loop ls_blo' + str(block) + '------')
                try:
                    genesis_block = block_chain[0]
                except:
                    genesis_block = None
                if block:
                    last_height = block.block_header.height
                else:
                    last_height = -1
                data = {
                    "last_height": -1,
                    "genesis_block": ""
                }
                if genesis_block:
                    data = {
                        "last_height": last_height,
                        "genesis_block": genesis_block.serialize()
                    }
                msg = Msg(Msg.HAND_SHAKE_MSG, data)
                self.send(msg)
        else:
            log.info("shake")
            block_chain = BlockChain()
            block = block_chain.get_last_block()
            log.info('------c s_loop ls_blo' + str(block) + '------')
            try:
                genesis_block = block_chain[0]
            except:
                genesis_block = None
            if block:
                last_height = block.block_header.height
            else:
                last_height = -1
            data = {
                "last_height": -1,
                "genesis_block": ""
            }
            if genesis_block:
                data = {
                    "last_height": last_height,
                    "genesis_block": genesis_block.serialize()
                }
            msg = Msg(Msg.HAND_SHAKE_MSG, data)
            self.send(msg)

    def handle_shake(self, msg):
        log.info("------client handle_shake from " +
                 str(self.ip) + "------")
        data = msg.get("data", "")
        last_height = data.get("last_height", 0)
        log.info("------with last height " + str(last_height) + "------")
        block_chain = BlockChain()
        block = block_chain.get_last_block()
        log.info('------c handle_sh ls_blo ' + str(block) + '------')
        if block:
            local_last_height = block.block_header.height
        else:
            local_last_height = -1
        log.info("client local_last_height %d, last_height %d" %
                 (local_last_height, last_height))
        if local_last_height > last_height:
            try:
                st = StopMine()
                log.info('------works------')
                if st.h < local_last_height:
                    st.h = local_last_height
            except:
                log.info('------dont work------')
            log.info("------error shake------")
            log.info("client local_last_height %d, last_height %d" %
                     (local_last_height, last_height))
            send_data = []
            for i in range(1, local_last_height + 1):
                block = None
                while not block:
                    try:
                        block = block_chain.get_block_by_height(i)
                        time.sleep(2)
                    except:
                        time.sleep(2)
                send_data.append(block.serialize())
            msg = Msg(Msg.SYNCHRONIZE_MSG, send_data)
            self.send(msg)
            log.info(
                "------client handle_shake send synchronize msg to" + str(self.ip) + "------")
        elif local_last_height < last_height:
            try:
                st = StopMine()
                log.info('------works------')
                if st.h < last_height:
                    st.h = last_height
                    st.ip = self.ip
                    log.info("------" + str(self.ip) + ' is the highest ' + str(st.h) + "------")
            except:
                log.info('------dont work------')
            start_height = 0 if local_last_height == -1 else local_last_height
            get_range = [start_height + 1, last_height + 1]
            send_msg = Msg(Msg.GET_BLOCK_MSG, get_range)
            self.send(send_msg)
        else:
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()
            # self.shake_loop()

    def handle_get_block(self, msg):
        datas = msg.get("data", "")
        log.info("------client handle_get_block from " +
                 str(self.ip) + "------")
        log.info("------with data " + str(datas) + "------")
        bc = BlockChain()
        log.info("------client deserialize block from peer------")
        try:
            st = StopMine()
            log.info('------works------')
            if st.ip != self.ip and st.ip:
                log.info('------not ip ' + str(st.ip) + '------')
                t = threading.Thread(target=self.shake_loop(), args=())
                t.start()
                return
        except:
            log.info('------failed to stop mine------')
        try:
            last_block = None
            while not last_block:
                last_block = bc.get_last_block()
                time.sleep(1)
            last_height = last_block.block_header.height
            for i in range(len(datas)-1, -1, -1):
                log.info("roll back others' block at " + str(i) + str(block))
                block = Block.deserialize(datas[i])
                if block.block_header.height > last_height:
                    log.info("last >> at " + str(last_height))
                    last_height -= 1
                    continue
                elif block.block_header.height == last_height:
                    last_height -= 1
                    local_block = None
                    while not local_block:
                        local_block = bc.get_block_by_height(block.block_header.height)
                        time.sleep(1)
                    if local_block != block:
                        log.info("not the same ")
                        log.info("local" + str(local_block))
                        log.info("block " + str(block))
                        utxo_set = UTXOSet()
                        utxo.roll_back(local_block)
                        bc.roll_back()
                    else:
                        log.info("the same at " + str(local_block.block_header.height))
                        break
                else:
                    log.info("local >> " + str(last_block.block_header.height))
                    t = threading.Thread(target=self.shake_loop(), args=())
                    t.start()
                    return
            last_height = last_block.block_header.height
            for data in datas:
                block = Block.deserialize(data)
                if block.block_header.height <= last_height:
                    continue
                elif block.block_header.height == last_height + 1:
                    last_height += 1
                    bc.add_block_from_peers(block, last_block)
                    log.info("c add block from peers " + str(block))
                    last_block = block
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()
        except:
            log.info(
                "------client handle_get_block failed------")
            t = threading.Thread(target=self.shake_loop(), args=())
            t.start()

    def handle_transaction(self, msg):
        log.info("------client handle_transaction------")
        data = msg.get("data", {})
        tx = Transaction.deserialize(data)
        tx_pool = TxPool()
        is_new = True
        if tx_pool.is_new(tx):
            log.info("------client never get this transaction before------")
            bc = BlockChain()
            ls_bl = bc.get_last_block()
            log.info('------c handle_tran ls_blo ' + str(ls_bl) + '------')
            if ls_bl:
                ls_height = ls_bl.block_header.height
                for i in range(0, ls_height + 1):
                    while True:
                        block = None
                        try:
                            block = bc.get_block_by_height(i)
                        except:
                            continue
                        if block:
                            break
                    bc_txs = block._transactions
                    for transaction in bc_txs:
                        if transaction.txid == tx.txid:
                            is_new = False
                            break
                    if not is_new:
                        break
            if is_new:
                tx_pool.add(tx)
                log.info(
                    "------client handel_transaction txpool added------")
                server2 = PeerServer()
                server2.broadcast_tx(tx)
                log.info("------client handle_transaction broadcast------")

        t = threading.Thread(target=self.shake_loop(), args=())
        t.start()
        # self.shake_loop()

    def handle_synchronize(self, msg):
        synchronize_range = msg.get("data", 1)
        block_chain = BlockChain()
        data = []
        log.info("------client handle_synchronize with range " +
                 str(synchronize_range[0]) + " " + str(synchronize_range[1]) + "------")
        for height in range(1, synchronize_range[1]):
            block = None
            while not block:
                try:
                    block = block_chain.get_block_by_height(height)
                    time.sleep(2)
                except:
                    time.sleep(2)
            data.append(block.serialize())
        msg = Msg(Msg.SYNCHRONIZE_MSG, data)
        self.send(msg)

    def handle_get_transaction(self, msg):
        log.info("------client handle_get_transaction------")
        tx_pool1 = TxPool()
        data = [tx.serialize() for tx in tx_pool1.txs]
        msg = Msg(Msg.TRANSACTION_MSG, data)
        self.send(msg)

    def handle_miss(self, msg):
        log.info("------client handle_miss------")
        tx_pool = TxPool()
        txs = msg.get("data", {})
        for tx_data in txs:
            log.info("------server handle_miss: for------")
            tx = Transaction.deserialize(tx_data)
            is_new = True
            if tx_pool.is_new(tx):
                log.info("------client miss this transaction before------")
                bc = BlockChain()
                ls_bl = bc.get_last_block()
                log.info('------c handle_m ls_blo ' + str(ls_bl) + '------')
                if ls_bl:
                    ls_height = ls_bl.block_header.height
                    for i in range(0, ls_height + 1):
                        while True:
                            block = None
                            try:
                                block = bc.get_block_by_height(i)
                            except:
                                continue
                            if block:
                                break
                        bc_txs = block._transactions
                        if bc_txs:
                            for transaction in bc_txs:
                                if transaction.txid == tx.txid:
                                    log.info("------old transaction------")
                                    log.info("------the id is: " +
                                             str(tx.txid) + "------")
                                    is_new = False
                                else:
                                    log.info("------brand new miss------")
                                    log.info("------the id is: " +
                                             str(tx.txid) + "------")
                        if not is_new:
                            break
                if is_new:
                    tx_pool.add(tx)
                    log.info("------client miss add this transaction------")
                    log.info("------the id is: " + str(tx.txid) + "------")
                    log.info("------client handle_miss broadcast------")
        t = threading.Thread(target=self.shake_loop(), args=())
        t.start()
        # self.shake_loop()

    def close(self):
        self.sock.close()


class PeerServer(Singleton):
    def __init__(self):
        if not hasattr(self, "peers"):
            self.peers = []
        if not hasattr(self, "nodes"):
            self.nodes = []
        if not hasattr(self, "ips"):
            self.ips = []
        if not hasattr(self, "longest_chain"):
            self.longest_chain = None
        if not hasattr(self, "time"):
            self.time = time.time()

    def get_ip(self, ifname='eth0'):  # enp2s0 # ens33
        env_dist = os.environ
        return env_dist.get('LOCAL_IP')
        # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # return socket.inet_ntoa(
        # fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(ifname[:15], 'utf-8')))[20:24])

    def nodes_find(self, p2p_server):
        log.info("------------")
        local_ip = self.get_ip()
        while True:
            nodes = p2p_server.get_nodes()
            log.info("-------------")
            for node in nodes:
                if node.ip not in self.ips:
                    log.info("------------nodes_find: " +
                             node.ip + "------------")
                    ip = node.ip
                    port = node.port
                    if local_ip == ip:
                        log.info("------local_ip==ip------")
                        continue
                    log.info("------------nodes ip: " +
                             node.ip + "------------")
                    client = TCPClient(ip, port)
                    log.info("------create TCPClient in nodes_find------")
                    t = threading.Thread(target=client.shake_loop, args=())
                    t.start()
                    log.info(
                        "------peer nodes_find: start the thread shake_loop------")
                    self.peers.append(client)
                    self.nodes.append(node)
                    self.ips.append(ip)
            time.sleep(1)

    def broadcast_tx(self, tx):
        log.info("------peerserver broadcast_tx------")
        for peer in self.peers:
            log.info("------peerserver broadcast for------")
            peer.add_tx(tx)
            log.info("------peerserver broadcast add------")

    def run(self, p2p_server):
        t = threading.Thread(target=self.nodes_find, args=(p2p_server,))
        t.start()


if __name__ == "__main__":
    tcpserver = TCPServer()
    tcpserver.listen()
    tcpserver.run()

    p2p = P2p()
    server = PeerServer()
    server.run(p2p)
    p2p.run()
