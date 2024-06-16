import hashlib
import random
import os


class ZKProof:
    def __init__(self):
        self.N = 20
        self.salt = os.urandom(16)

    def _hash(self, x):
        return hashlib.sha256(x.encode('utf-8') + self.salt).hexdigest()

    def generate_proof(self, secret):
        self.secret = secret
        self.v = self._hash(secret)
        r = str(random.randint(1, self.N))
        self.x = self._hash(r)
        return self.x

    def get_secret(self):
        return self.secret

    def verify(self, response):
        return self.v == self._hash(response)


exports = {
    'zkp': ZKProof
}
