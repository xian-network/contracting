'''
This module decorates mysql_intermediate adding single point in time snapshotting
(SPITS).

It contains additional functions:
* spits_commit()
* spits_rollback()
* spits_purge()
* spits_verify_clean()

TODO: sql escapes
def sql_escapes(s):
    # TODO: make sure everything I need is here.
    import re
    return re.sub("'", "''", s)


Old notes:
* mysql-point-in-time (commit/rollback to PIT)
  * stuff to figure out
    * Does MyRocks store nulls efficiently?
      If no, rollback row data shouldn't live in same table
      * In that case, does myrocks store empty tables efficiently, can it move rows betweeen tables efficiently
        If so, store rollback data in dedicated tables.
  * additional data
    * Rollback/commit instructions table (not specific to any contract)
      * Rollback pending changes
      * Commit changes
    * Duplicate columns in tables, use a disallowed character with label, something like original_data$<column_name>
  * decorates base lib functions
    * select
      * hides restricted data
        * original_data columns
        * soft-deleted rows where rollback_action = undelete
        * soft-deleted columns
        * block access to soft deleted tables
    * create table
      * Restricts characters for Scratch namespacing
      * Additional columns for
        * rollback_action [restore, delete, undelete]
        * original_data$<column_name> for every column
    * insert row
      * Insert normally, but include rollback_action = delete
      * Obviously don't allow data writes to original_data fields
    * delete row
      * If rollback_action is null
        * Set rollback_action = undelete
        * move data to original_data columns (needed for columns with unique constraint)
    * update row
      * If rollback_action is null
        * Set rollback_action = restore
        * move data to original_data columns
    * Add column
      * add drop column x on table y command to rollback table unless column with same name already dropped
        * i.e. if a column is dropped and readded and dropped again in the same scratch window, just throw it out
          * remember this is a point-in-time snapshot, not an undo-stack
    * drop column
      * if column existed before window save with prepended name
    * drop table
      * if table existed before scratch window, move it to a temporary name
  * additional functionality for
    * begin_scratch(window_id)
      * creates scratch_data table if none exists
    * commit_scratch(window_id)
    * rollback_scratch(window_id)
'''

import mysql_intermediate as m


def bind_passthrough(imported_module, name):
    globals()[name] = getattr(imported_module, name)


to_passthrough = [
  'ColumnDefinition',
  'AutoIncrementColumn',
  'QueryCriterion',
  'format_where_clause',
]

for p in to_passthrough:
    bind_passthrough(m, p)


'''
Need additional query features: aggregated criteria, list tables should be more flexible
Other features needed: batched execution

class CreateTable(object):
    * Validation
      * Make sure table name doesn't contain spits token
      * Make sure column names don't contain spits token
    * Write rollback command delete table to spits table
    * Append column definitions, duplicate everything prepended with spits token, $spits_preserve$_ (or something)
    * Append column definitions with spits_rollback_strategy column
    * Create table

class DeleteRows(object):
    * Add deleted flag to spits_rollback_strategy column

class UpdateRows(object):
    * If spits_rollback_stategy is empty
      * copy original columns to $spits_preserve$ columns
      * set spits_rollback_strategy column to recover flag
    * else update in place

class InsertRows(object):
    * Insert normally but set $spits_rollback_strategy$ to 'delete'

class SelectRows(object):
    * If *, describe table and populate fields without $spits_preserve$* and spits_rollback_strategy
    * If user manually adds $spits_preserve$* and spits_rollback_strategy, fail.
      * Figure out how to propagte the failure without making the abstraction leaky
    * AND or if none exists, add to criteria 'NOT spits_rollback_strategy=undelete'

class DescribeTable(object):
    * Describe normally, but omit $spits_preserve$* and $spits_rollback_strategy$

class ListTables(object):
    * List tables, but omit $spits_deleted$* tables and spits table

class AddTableColumn(object):
    * Add two columns, the requested column and the $spits_preserve$_ column
    * Add delete column command to spits table

class DropTableColumn(object):
    * rename column $spits_deleted$_
    * Add undelete column command to spits table

class DropTable(object):
    * move to $spits_deleted$_
'''
