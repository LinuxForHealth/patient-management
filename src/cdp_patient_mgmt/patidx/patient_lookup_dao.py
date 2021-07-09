from whpa_cdp_postgres import postgres
from .patient_lookup_data import PatientMasterIndexModelDbRecord
from typing import List

_tenant_db_map = {}

async def _get_tenant_db_pool(tenant_id: str) -> postgres.Postgres:
    global _tenant_db_map
    if tenant_id not in _tenant_db_map:
        db_pool = await postgres.create_postgres_pool(tenant_id)
        _tenant_db_map[tenant_id] = db_pool    
    
    return _tenant_db_map[tenant_id]
    

async def patient_lookup(tenant_id: str, lookup_set):
    db = await _get_tenant_db_pool(tenant_id)
    row = await db.fetch('SELECT * FROM unnest($1::text[]) m(requested_id) '
                         'LEFT OUTER JOIN cdp_idx.patient_master_index pmx ON m.requested_id=pmx.pmidx_id;',
                         lookup_set)
    return row


async def create_entries(tenant_id: str, master_id, patient_id_type, entries: List[PatientMasterIndexModelDbRecord]):
    db_records: str = '\'{'
    first_entry = True
    for entry in entries:
        if first_entry:
            db_records = db_records + entry.get_db_record_list()
            first_entry = False
        else:
            db_records = db_records + ', ' + entry.get_db_record_list()

    db_records = db_records + '}\'::cdp_idx.patient_master_index[]'

    select_function_string = '(SELECT cdp_idx.fn_create_patient_entries({0},\'{1}\',{2}))'.format(master_id,
                                                                                                  patient_id_type,
                                                                                                  db_records)
    db = await _get_tenant_db_pool(tenant_id)
    row = await db.fetch(f'SELECT * FROM {select_function_string} n;')
    return row
