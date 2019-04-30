from unittest import TestCase
from contracting.ast.linter import Linter
import ast
from contracting.ast.whitelists import ALLOWED_AST_TYPES


class TestLinter(TestCase):
    def setUp(self):
        self.l = Linter()

    def test_linter(self):
        # log = get_logger("TestSenecaLinter")
        data = '''
@export
def a():
    b = 10
    return b
    '''

        print("stu code: \n{}".format(data))
        ptree = ast.parse(data)
        status = self.l.check(ptree)
        self.l.dump_violations()
        if status is None:
            print("Success!")
        else:
            print("Failed!")

        self.assertEqual(status, None)

    def test_good_ast_type(self):
        for t in ALLOWED_AST_TYPES:
            _t = t()
            self.l.ast_types(_t, 1)
            self.assertListEqual([], self.l._violations)

    def test_bad_ast_type(self):
        err = 'Line 1 : S1- Illegal contracting syntax type used : AsyncFunctionDef'
        t = ast.AsyncFunctionDef()
        self.l.ast_types(t, 1)
        self.l.dump_violations()
        self.assertMultiLineEqual(err, self.l._violations[0])

    def test_not_system_variable(self):
        v = 'package'
        self.l.not_system_variable(v, 1)
        self.l.dump_violations()
        self.assertListEqual([], self.l._violations)

    def test_system_variable(self):
        v = '__package__'
        err = "Line 1 : S2- Illicit use of '_' before variable : __package__"
        self.l.not_system_variable(v, 1)
        self.l.dump_violations()
        self.assertMultiLineEqual(err, self.l._violations[0])

    '''
    Is blocking all underscore variables really the solution to preventing access to system variables?
    '''
    def test_not_system_variable_ast(self):
        code = '''
@export
def a():
    __ruh_roh__ = 'shaggy'
        '''
        err = "Line 4 : S2- Illicit use of '_' before variable : __ruh_roh__"

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertMultiLineEqual(err, self.l._violations[0])

    def test_not_system_variable_ast_success(self):
        code = '''
@export
def a():
    ruh_roh = 'shaggy'
        '''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, None)
        self.assertListEqual([], self.l._violations)

    # def test_visit_async_func_def_fail(self):
    #     err = 'Error : Illegal AST type: AsyncFunctionDef'
    #     n = ast.AsyncFunctionDef()
    #
    #     self.l.visit_AsyncFunctionDef(n)
    #     self.l.dump_violations()
    #     self.assertMultiLineEqual(err, self.l._violations[0])

    def test_visit_async_func_def_fail_code(self):
        code = '''
@export
async def a():
    ruh_roh = 'shaggy'
def b():
    c = 1 + 2
'''
        err = 'Line 2: S7- Illicit use of Async functions'

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(len(chk), 2)
        self.assertMultiLineEqual(err, self.l._violations[0])

#TODO failing
    # def test_visit_class_fail(self):
    #     err = 'Error : Illegal AST type: ClassDef'
    #     n = ast.ClassDef()
    #     self.l.visit_ClassDef(n)
    #     self.l.dump_violations()

        # self.assertMultiLineEqual(err, self.l._violations[0])

    def test_visit_class_fail_code(self):
        code = '''
class Scooby:
    pass
        '''
        err = 'Line 2: S6- Illicit use of classes'

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(len(chk), 2)
        self.assertMultiLineEqual(err, self.l._violations[0])

    def test_accessing_system_vars(self):
        code = '''
@export
def a():
    ruh_roh = 'shaggy'
    ruh_roh.__dir__()
'''
        err = "Line 5 : S2- Illicit use of '_' before variable : __dir__"
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertMultiLineEqual(err, self.l._violations[0])

    def test_accessing_attribute(self):
        code = '''
@export
def a():
    ruh_roh = 'shaggy'
    ruh_roh.capitalize()
    '''

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, None)
        self.assertListEqual([], self.l._violations)

#TODO failed test case

    def test_no_nested_imports(self):
        code = '''
@export
def a():
    import something
        '''

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, ['Line 2: S3- Illicit use of Nested imports'])

    def test_no_nested_imports_works(self):
        code = '''
@export
def a():
    ruh_roh = 'shaggy'
    ruh_roh.capitalize()
            '''

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, None)
        self.assertListEqual([], self.l._violations)

    def test_augassign(self):
        code = '''
@export
def a():
    b = 0
    b += 1
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, None)
        self.assertListEqual([], self.l._violations)

    def test_no_import_from(self):
        code = '''
from something import a
@export
def a():
    b = 0
    b += 1
'''
        err = 'Line 2: S4- ImportFrom ast nodes not yet supported'

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertMultiLineEqual(err, self.l._violations[0])

# disabling import check it would be done by compiler

#     def test_import_non_existent_contract(self):
#         code = '''
# import something
# @export
# def a():
#     b = 0
#     b += 1
# '''
#         err = 'Line 2: S5- Contract not found in lib: something'
#
#         c = ast.parse(code)
#         self.l.check(c)
#         self.l.dump_violations()
#         self.assertMultiLineEqual(err, self.l._violations[0])

    def test_final_checks_set_properly(self):
        code = '''
def a():
    b = 0
    b += 1
        '''

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk, ['Line 0: S13- No valid contracting decorator found'])
        self.assertFalse(self.l._is_one_export)

    def test_collect_function_defs(self):
        code = '''
@export
def a():
    return 42

@export
def b():
    return 1000000

@export
def x():
    return 64

@export
def y():
    return 24
'''
        c = ast.parse(code)
        self.l._collect_function_defs(c)
        self.l.dump_violations()
        self.assertEqual(self.l._functions, ['a', 'b', 'x', 'y'])

    def test_assignment_of_import(self):
        code = '''
import import_this

@export
def test():
    a = import_this.howdy()
    a -= 1000
    return a        
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()

    def test_good_orm_initialization(self):
        code = '''
v = Variable()

@export
def set(i):
    v.set(i)
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.assertEqual(self.l._violations, [])

    def test_bad_orm_initialization(self):
        code = '''
v = Variable(contract='currency', name='stus_balance')

@export
def set(i):
    v.set(i)
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.assertEqual(chk[0], 'Line 2: S11- Illicit keyword overloading for ORM assignments')

    def test_multi_targets_orm_fails(self):
        code = '''
v, x = Variable()

@export
def set(i):
    v.set(i)
    '''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        print(chk)
        self.assertEqual(chk[0], 'Line 2: S12- Multiple targets to ORM definition detected')

    def test_multi_decorator_fails(self):
        code = '''
@construct
@export
def kaboom():
    print('i like to break things')
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk[0], 'Line 2: S10- Illicit use of multiple decorators: Detected: 2 MAX limit: 1')

    def test_invalid_decorator_fails(self):
        code = '''
@seneca_invalid
def wont_work():
    print('i hope')
'''
        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()
        self.assertEqual(chk[0], 'Line 2: S8- Invalid decorator used: valid list: seneca_invalid')

    def test_multiple_constructors_fails(self):
        code = '''
@construct
def seed_1():
    print('hi')
    
@construct
def seed_2():
    print('howdy')
'''

        c = ast.parse(code)
        chk = self.l.check(c)
        self.l.dump_violations()

        self.assertEqual(len(chk),2)
        self.assertEqual(self.l._violations, [chk[0], 'Line 0: S13- No valid contracting decorator found'])