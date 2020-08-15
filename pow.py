# coding:utf-8
import time
import sys
import utils
from errors import NonceNotFoundError
from stopmine import StopMine

class ProofOfWork(object):
    """
    pow
    """
    _N_BITS = 1    # e1
    MAX_BITS = 256
    MAX_SIZE = sys.maxsize
    def __init__(self, block, n_bits=_N_BITS):
        self._n_bits = n_bits
        self._target_bits = 1 << (self.MAX_BITS - n_bits)
        self._block = block

    def _prepare_data(self, nonce):
        data_lst = [str(self._block.block_header.prev_block_hash),
                    str(self._block.block_header.hash_merkle_root),
                    str(self._block.block_header.timestamp),
                    str(self._block.block_header.height),
                    str(nonce)]
        return utils.encode(''.join(data_lst))

    def run(self):
        nonce = 0
        found = False
        hash_hex = None
        while nonce < self.MAX_SIZE:
            data = self._prepare_data(nonce)
            hash_hex = utils.sum256_hex(data)

            hash_val = int(hash_hex, 16)
            # sys.stdout.write("data: %s\n" % data) # 7.11
            # sys.stdout.write("try nonce == %d\thash_hex == %s \n" % (nonce, hash_hex))    # 7.11
            if (hash_val < self._target_bits):
                found = True
                break

            nonce += 1
        if found:
            for i in range(0, 60):
                try:
                    st = StopMine()
                    if st.h >= st.mine_h:
                       raise NonceNotFoundError
                    time.sleep(1)
                except:
                    time.sleep(1)
        else:
            # print('Not Found nonce')
            raise NonceNotFoundError('nonce not found')
        return nonce, hash_hex

    def validate(self):
        """
        validate the block
        """
        data = self._prepare_data(self._block.block_header.nonce)
        # print("data:"+str(data))    # change delete
        hash_hex = utils.sum256_hex(data)
        hash_val = int(hash_hex, 16)
        # print(hash_hex) # change delete
        return hash_val < self._target_bits
