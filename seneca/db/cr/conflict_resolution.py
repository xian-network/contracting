from collections import defaultdict
from ...logger import get_logger
from typing import List


# TODO this assumes stamps_to_tau will never change. We need more intricate logic to handle the case where it does...
STAMPS_KEY = 'currency:balances:black_hole'
CR_EXCLUDED_KEYS = ['currency:xrate:TAU_STP', STAMPS_KEY]


class CRDataGetSet(dict):
    def __init__(self, master_db, working_db):
        super().__init__()
        self.log = get_logger(type(self).__name__)
        self.master, self.working = master_db, working_db
        self.writes = defaultdict(set)
        self.outputs = defaultdict(str)
        self.redo_log = defaultdict(dict)

    def _get_modified_keys(self):
        return set().union((key for key in self if self[key]['og'] != self[key]['mod'] and self[key]['mod'] is not None))

    def get_state_for_idx(self, contract_idx: int) -> str:
        """
        Gets a state representation string for a particular contract index. """
        return self.outputs[contract_idx]

    def reset_contract_data(self, contract_idx: int):
        """ Resets the reads list and modification list for the contract at index idx. """
        self.writes[contract_idx].clear()
        self.outputs[contract_idx] = ''

    def merge_to_common(self):
        modified_keys = self._get_modified_keys()
        for key in modified_keys:
            self.working.set(key, self[key]['mod'])

    @classmethod
    def merge_to_master(cls, working_db, master_db, key: str):
        assert working_db.exists(key), "Key {} must exist in working_db to merge to master".format(key)
        val = working_db.get(key)
        master_db.set(key, val)

    def get_state_rep(self) -> str:
        """
        Return a representation of all ledis DB commands to update to the absolute state in minimum operations
        :return: A string with all ledis command in raw executable form, delimited by semicolons
        """
        modified_keys = self._get_modified_keys()
        # Need to sort the modified_keys so state output is deterministic
        return ''.join('SET {} {};'.format(k, self[k]['mod'].decode()) for k in sorted(modified_keys))

    def rollback_contract(self, contract_idx: int):
        self.log.debug("Reseting contract idx {}".format(contract_idx))
        if contract_idx not in self.redo_log:
            # TODO for dev, we raise an exception, as we do not expect contracts to read only w/o writing
            # raise Exception("Contract idx {} not in redo_log!".format(contract_idx))
            self.log.warning("Contract idx {} not in redo_log! Returning without any reverts".format(contract_idx))
            return

        self.reset_contract_data(contract_idx)

        for key in self.redo_log[contract_idx]:
            og_val = self.redo_log[contract_idx][key]
            # Remove the key entirely if value is none
            if og_val is None:
                self.log.debugv("Removing key {}".format(key))
                del self[key]
            # Otherwise, reset_db the key to the value before the contract
            else:
                self.log.debugv("Resetting key {} to value {}".format(key, og_val))
                self[key]['mod'] = og_val

            # Remove this contract idx from the key's affected contracts
            if key in self and contract_idx in self[key]['contracts']:
                self[key]['contracts'].remove(contract_idx)

    def revert_contract(self, contract_idx: int):
        assert contract_idx in self.redo_log, "Contract index {} not found in redo log!".format(contract_idx)

    def get_rerun_list(self, reset_keys=True) -> List[int]:
        mod_keys = self.get_modified_keys_recursive()
        assert STAMPS_KEY not in mod_keys, "Noooooooo mod keys {} has stamp key".format(mod_keys)
        contract_set = set()
        self.log.debugv("Modified keys for rerunning: {}".format(mod_keys))

        for key in mod_keys:
            contract_set = contract_set.union(self[key]['contracts'])
            if reset_keys:
                self.reset_key(key)

        self.log.debugv("CONTRACT SET TO RERUN: {}".format(contract_set))

        return sorted(contract_set)

    def get_modified_keys(self) -> set:
        mods = set()
        for k in self:
            if (self.master.exists(k) and (self.master.get(k) != self[k]['og'])) or (
                    self.working.exists(k) and (self.working.get(k) != self[k]['og'])):
                mods.add(k)

        return mods - {STAMPS_KEY, *CR_EXCLUDED_KEYS}

    def get_modified_keys_recursive(self) -> set:
        mod_keys = self.get_modified_keys()
        self.add_adjacent_keys(mod_keys)
        return mod_keys - {STAMPS_KEY, *CR_EXCLUDED_KEYS}

    def add_adjacent_keys(self, key_set):
        copy_set = set(key_set)  # we must copy the set so we can modify the real while while enumerating
        for key in copy_set:
            self._add_adjacent_keys(key, key_set)

    def _add_adjacent_keys(self, key: str, key_set: set):
        assert key in key_set, 'logic error'
        assert key in self, 'key is not in self??'

        # Get all keys modified in conjunction with 'key'
        new_keys = set()
        for contract_idx in self[key]['contracts']:
            new_keys = new_keys.union(self.writes[contract_idx])

        # Recursive stage
        for k in new_keys:
            if k in key_set:  # Base case -- if this key is already in the key_list do not recurse
                continue
            else:
                key_set.add(k)
                self._add_adjacent_keys(k, key_set)

    def reset_key(self, key):
        self.log.debugv("Resetting key {}".format(key))
        og_val = self[key]['og']

        self[key]['mod'] = None
        self[key]['contracts'] = set()

        if self.working.exists(key) and self.working.get(key) != og_val:
            self.log.debugv("Reseting key {} to COMMON value {}".format(key, self.working.get(key)))
            self[key]['og'] = self.working.get(key)
        elif self.master.exists(key) and self.master.get(key) != og_val:
            self.log.debugv("Reseting key {} to MASTER value {}".format(key, self.master.get(key)))
            self[key]['og'] = self.master.get(key)
        else:
            self.log.spam("No updated value found for key {}. Clearing modified and leaving original val".format(key))


class CRContext:

    def __init__(self, working_db, master_db, sbb_idx: int, finalize=False):
        self.log = get_logger(type(self).__name__)
        self.working_db, self.master_db = working_db, master_db
        self.sbb_idx = sbb_idx

        self.cr_data = CRDataGetSet(self.master_db, self.working_db)

        # TODO deques are probobly more optimal than using arrays here
        # run_results is a list of strings, representing the return code of contracts (ie 'SUCC', 'FAIL', ..)
        self.run_results = []
        self.contracts = []  # A list of ContractionTransaction objects. SenecaClient should append as it runs contracts
        self.input_hash = None  # Input hash should be set by SBBClient once a new sub block is started
        self.merged_to_common = False

        # 'locked' is a debug flag to detect with CR data is being written to when it shouldnt be. If locked, no
        # acceses to underlying self.cr_data is expected. We lock the CRContext when we put it in available_dbs,
        # and unlock it when we put it in pending_dbs or active_dbs, but only while we are running contracts
        self.locked = True

    @property
    def next_contract_idx(self):
        assert len(self.contracts) == len(self.run_results), "Oh dear...a logic error is present"  # TODO remove
        return len(self.contracts)

    def add_contract_result(self, contract, result: str):
        assert len(self.contracts) == len(self.run_results), "Oh dear...a logic error is present"  # TODO remove
        self.contracts.append(contract)
        self.run_results.append(result)

    def update_contract_result(self, contract_idx: int, result: str):
        assert len(self.contracts) == len(self.run_results), "Oh dear...a logic error is present"  # TODO remove
        assert len(self.contracts) > contract_idx, "contract_idx {} out of bounds. Only {} contracts in self.contracts" \
            .format(contract_idx, len(self.contracts))
        self.log.debugv("Updating run result for contract idx {} to <{}>".format(contract_idx, result))
        self.run_results[contract_idx] = result

    def rollback_contract(self, contract_idx: int):
        # TODO this only works for set/get
        self.cr_data['getset'].rollback_contract(contract_idx)

    def reset_run_data(self):
        """ Resets all state held by this container. """
        self.log.debug("Resetting run data for CRData with ".format(self.input_hash, id(self)))

        # Reset this object's state
        self.run_results.clear()
        self.contracts.clear()
        self.merged_to_common = False
        self.input_hash = None

        # TODO is this ok resetting all the CRData's like this? Should we worry about memory leaks? --davis
        self.cr_data = CRDataGetSet(self.master_db, self.working_db)

    def reset_db(self):
        self.log.debug(
            "CRData resetting working db #{}".format(self.working_db.connection_pool.connection_kwargs['db']))
        self.working_db.flushdb()

    def assert_reset(self):
        """ Assert this object has been reset_db properly. For dev purposes. """

        old_locked_val = self.locked
        self.locked = False

        err = "\nContracts: {}\nRun Results: {}\nWrites: {}\nOutputs: {}\nRedo Log: {}\nInput hash: {}\n" \
            .format(self.contracts, self.run_results, self.cr_data.writes,
                    self.cr_data.outputs, self.cr_data.redo_log, self.input_hash)
        assert len(self.contracts) == 0, err
        assert len(self.run_results) == 0
        assert len(self.cr_data.writes) == 0, err
        assert len(self.cr_data.outputs) == 0, err
        assert len(self.cr_data.redo_log) == 0, err
        assert not self.merged_to_common
        assert self.input_hash is None, "Input hash not reset. (self.input_hash={})".format(self.input_hash)

        self.locked = old_locked_val

    def get_state_for_idx(self, contract_idx: int) -> str:
        """
        Returns the state for the contract at the specified index
        """
        assert contract_idx < len(self.contracts), "Contract index {} out of bounds for self.contracts of length {}" \
            .format(contract_idx, len(self.contracts))

        state_str = ''
        state_str += self.cr_data.get_state_for_idx(contract_idx)
        return state_str

    def get_subblock_rep(self) -> List[tuple]:
        """
        Returns a list of tuples. There will be one tuple for each contract in self.contracts, and tuples will be of the
        form (contract, status, state). contract will be an instance of ContractTransaction. Status will be a string
        representing the execution status of the contract (fail/succ/ect). State will be a string that represents the
        changes to state made by that contract.
        """
        assert len(self.contracts) == len(self.run_results), "you done shit the bed again davis"
        assert self.merged_to_common, "You should have merged to common before trying to get the subblock rep"

        return [(self.contracts[i], self.run_results[i], self.get_state_for_idx(i)) for i in range(len(self.contracts))]

    def iter_rerun_indexes(self):
        # TODO this only works for getset right now
        # TODO this does not support new keys being modified during the rerun process
        data = self.cr_data['getset']
        contract_list = data.get_rerun_list()
        self.log.info("Contracts indexes to rerun: {}".format(contract_list))

        # DEBUG -- TODO DELETE
        # self.log.notice("CRData with input hash {}".format(self.input_hash))
        # self.log.notice("CRData with id {}".format(id(self)))
        # self.log.notice("CRData contracts length: {}".format(len(self.contracts)))
        # self.log.info("data reads: {}".format(data.reads))
        # self.log.info("data writes: {}".format(data.writes))
        # END DEBUG

        for i in contract_list:
            self.log.debugv("Rerunning contract at index {}".format(i))
            og_reads, og_writes = data.reads[i], data.writes[i]
            self.reset_contract_data(i)

            yield i

            # TODO handle this behavior by reverting and failing until we have a better mechanism
            assert og_reads == data.reads[i], "Original reads have changed for contract idx {}!\nOriginal: {}\nNew " \
                                              "Reads: {}".format(i, og_reads, data.reads[i])
            assert og_writes == data.writes[i], "Original writes have changed for contract idx {}!\nOriginal: {}\nNew " \
                                                "Writes: {}".format(i, og_writes, data.writes[i])

    def reset_contract_data(self, contract_idx: int):
        """
        Resets the reads list and modification list for the contract at index idx.
        """
        for obj in self.cr_data.values():
            obj.reset_contract_data(contract_idx)

    def merge_to_common(self):
        assert not self.merged_to_common, "Already merged to common! merge_to_common should only be called once"
        self.cr_data.merge_to_common()
        self.merged_to_common = True

    @classmethod
    def merge_to_master(cls, working_db, master_db):
        from seneca.db.cr.client import Macros  # to avoid cyclic imports
        keys = working_db.keys()
        for key in keys:
            # Ignore Phase keys
            if key in Macros.ALL_MACROS:
                continue

            CRDataGetSet.merge_to_master(working_db, master_db, key)

    def __repr__(self):
        return "<CRContext(input_hash={} .., contracts run so far={}, working db num={})>".format(
            self.input_hash[:16], len(self.contracts), self.working_db.connection_pool.connection_kwargs['db'])

