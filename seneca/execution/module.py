import sys

from importlib.abc import Loader, MetaPathFinder
from importlib import invalidate_caches

from seneca.config import DB_URL, DB_PORT, DB_DELIMITER

from seneca.storage.driver import DatabaseDriver, ContractDriver

'''
    This module will remain untested and unused until we decide how we want to 'forget' importing.
'''


def uninstall_builtins():
    sys.meta_path.clear()
    sys.path_hooks.clear()
    sys.path.clear()
    sys.path_importer_cache.clear()
    invalidate_caches()


def install_database_loader():
    sys.meta_path.append(DatabaseFinder)


def uninstall_database_loader():
    sys.meta_path.remove(DatabaseFinder)


'''
    Is this where interaction with the database occurs with the interface of code strings, etc?
    IE: pushing a contract does sanity checks here?
'''


class DatabaseFinder(MetaPathFinder):
    def find_module(fullname, path, target=None):
        return DatabaseLoader()


class DatabaseLoader(Loader):
    def __init__(self):
        self.d = ContractDriver()

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        # fetch the individual contract
        code = self.d.get_contract(module.__name__)
        exec(code, vars(module))

    def module_repr(self, module):
        return '<module {!r} (smart contract)>'.format(module.__name__)


