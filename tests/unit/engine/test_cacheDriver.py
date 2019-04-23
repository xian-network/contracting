from unittest import TestCase
from seneca.db.driver import CacheDriver
from collections import deque

class TestCacheDriver(TestCase):
    def setUp(self):
        self.c = CacheDriver()
        self.c.conn.flushdb()

    def tearDown(self):
        self.c.conn.flushdb()

    def test_get_from_db_if_not_in_modified_keys(self):
        self.c.conn.set('test', 'val1')

        val = self.c.get('test')
        self.assertEqual(val, b'val1')

    def test_get_from_contract_modification_if_already_set(self):
        update = {'test': 'val2'}

        self.c.contract_modifications[-1].update(update)
        self.c.modified_keys.update({'test': 0})

        self.c.conn.set('test', 'val1')

        val = self.c.get('test')

        self.assertEqual(val, 'val2')

    def test_get_from_contract_modification_chains(self):
        update = {'test': 'val2', 'stu': 1234, 'colin': 0}
        self.c.contract_modifications[-1].update(update)
        self.c.modified_keys.update({'test': 0, 'stu': 1234, 'colin': 0})

        update = {'test': 'val3'}
        self.c.contract_modifications.append(update)
        self.c.modified_keys.update({'test': 1})

        update = {'stu': 500000}
        self.c.contract_modifications.append(update)
        self.c.modified_keys.update({'stu': 2})

        update = {'colin': 1000000}
        self.c.contract_modifications.append(update)
        self.c.modified_keys.update({'colin': 3})

        self.assertEqual(self.c.get('test'), 'val3')
        self.assertEqual(self.c.get('stu'), 500000)
        self.assertEqual(self.c.get('colin'), 1000000)

    def test_basic_set_writes_to_contract_modifications_and_modified_keys(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.assertDictEqual(self.c.modified_keys, {'stu': deque([0]), 'col': deque([0]), 'raghu': deque([0])})
        self.assertDictEqual(self.c.contract_modifications[-1], {'stu': 'farm', 'col': 'bro', 'raghu': 'set'})

    def test_new_tx_adds_length_to_contract_modifications(self):
        self.c.new_tx()
        self.assertEqual(len(self.c.contract_modifications), 2)

    def test_new_tx_creates_new_key_space(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.assertDictEqual(self.c.modified_keys, {'stu': deque([0]), 'col': deque([0, 1]), 'raghu': deque([0, 1])})

    def test_new_tx_creates_new_key_space_and_gets_correct_keys(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.assertEqual(self.c.get('raghu'), 'tes')
        self.assertEqual(self.c.get('stu'), 'farm')
        self.assertEqual(self.c.get('col'), 'orb')

    def test_commit_resets_state(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.c.commit()

        self.assertDictEqual(self.c.contract_modifications[-1], {})
        self.assertDictEqual(self.c.modified_keys, {})

    def test_commit_writes_to_db(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.c.commit()

        s = self.c.conn.get('stu')
        c = self.c.conn.get('col')
        r = self.c.conn.get('raghu')

        self.assertEqual(s, b'farm')
        self.assertEqual(c, b'orb')
        self.assertEqual(r, b'tes')

    def test_revert_idx_0_resets(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.revert()

        self.assertDictEqual(self.c.contract_modifications[-1], {})
        self.assertDictEqual(self.c.modified_keys, {})

    def test_revert_idx_1_resets_to_contract_0_modifications(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.c.revert(1)

        print(self.c.contract_modifications)
        print(self.c.modified_keys)

        self.assertEqual(self.c.get('stu'), 'farm')
        self.assertEqual(self.c.get('col'), 'bro')
        self.assertEqual(self.c.get('raghu'), 'set')

    def test_revert_idx_2_resets_to_contract_1(self):
        self.c.set('stu', 'farm')
        self.c.set('col', 'bro')
        self.c.set('raghu', 'set')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('raghu', 'tes')

        self.c.new_tx()

        self.c.set('col', 'orb')
        self.c.set('stu', 'tes')
        self.c.set('new', '1')

        self.c.new_tx()

        self.c.set('stu', 'abc')
        self.c.set('col', 'yyy')
        self.c.set('raghu', 'xxx')
        self.c.set('new', '2')

        self.c.revert(2)

        print(self.c.contract_modifications)
        print(self.c.modified_keys)

        self.assertEqual(self.c.get('stu'), 'farm')
        self.assertEqual(self.c.get('col'), 'orb')
        self.assertEqual(self.c.get('raghu'), 'tes')
        self.assertEqual(self.c.get('new'), None)