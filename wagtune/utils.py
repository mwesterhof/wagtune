import random
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from base64 import b64encode, b64decode


def get_randomized_for_seed(visitor_key, page_id=1, min_value=0, max_value=1024):
    seed = visitor_key * page_id
    local_random = random.Random()
    local_random.seed(seed)
    return local_random.randint(min_value, max_value)


class TokenProcessor:
    def __init__(self):
        key = os.urandom(32)
        self.iv = os.urandom(16)
        self.cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv))

    def generate_token(self, abtest_parent_id, abtest_variant_id, abtest_revision_id):
        to_encrypt = bytes(f'{abtest_parent_id}:{abtest_variant_id}:{abtest_revision_id}'.ljust(16), 'utf-8')

        encryptor = self.cipher.encryptor()
        return str(
            b64encode(encryptor.update(to_encrypt) + encryptor.finalize()),
            'utf-8'
        )

    def unpack_token(self, token_encoded):
        token = b64decode(token_encoded)
        decryptor = self.cipher.decryptor()
        decrypted = decryptor.update(token) + decryptor.finalize()
        abtest_parent_id, abtest_variant_id, abtest_revision_id = str(decrypted, 'utf-8').split(':')

        return int(abtest_parent_id), int(abtest_variant_id), int(abtest_revision_id)


token_processor = TokenProcessor()
