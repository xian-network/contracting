from contracting.stdlib.bridge.orm import exports as orm_exports
from contracting.stdlib.bridge.hashing import exports as hash_exports
from contracting.stdlib.bridge.time import exports as time_exports
from contracting.stdlib.bridge.random import exports as random_exports
from contracting.stdlib.bridge.imports import exports as imports_exports
from contracting.stdlib.bridge.access import exports as access_exports
from contracting.stdlib.bridge.decimal import exports as decimal_exports
from contracting.stdlib.bridge.crypto import exports as crypto_exports
from contracting.stdlib.bridge.zkp import exports as zkp_exports

# TODO create a module instead and return it inside of a dictionary like:
# {
#    'stdlib': module
# }
#
# Then stdlib.datetime becomes available, etc


def gather():
    env = {}

    env.update(orm_exports)
    env.update(hash_exports)
    env.update(time_exports)
    env.update(random_exports)
    env.update(imports_exports)
    env.update(access_exports)
    env.update(decimal_exports)
    env.update(crypto_exports)
    env.update(zkp_exports)

    return env
