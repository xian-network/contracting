fh = ForeignHash(foreign_contract='test_orm_hash_contract', foreign_name='h')

@seneca_export
def set_fh(k, v):
    fh.set(k, v)

@seneca_export
def get_fh(k):
    return fh.get(k)
