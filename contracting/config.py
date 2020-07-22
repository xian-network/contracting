DB_OFFSET = 1
NUM_CACHES = 4

RECURSION_LIMIT = 1024

DELIMITER = ':'
INDEX_SEPARATOR = '.'

DECIMAL_PRECISION = 64

PRIVATE_METHOD_PREFIX = '__'
EXPORT_DECORATOR_STRING = 'export'
INIT_DECORATOR_STRING = 'construct'
INIT_FUNC_NAME = '__{}'.format(PRIVATE_METHOD_PREFIX)
VALID_DECORATORS = {EXPORT_DECORATOR_STRING, INIT_DECORATOR_STRING}

ORM_CLASS_NAMES = {'Variable', 'Hash', 'ForeignVariable', 'ForeignHash'}

MAX_HASH_DIMENSIONS = 16
MAX_KEY_SIZE = 1024
MAX_VALUE_SIZE = 32 * 1024

READ_COST_PER_BYTE = 3
WRITE_COST_PER_BYTE = 25

STAMPS_PER_TAU = 20
