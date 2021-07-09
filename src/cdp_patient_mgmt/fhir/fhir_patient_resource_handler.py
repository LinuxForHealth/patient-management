from fhir.resources.patient import Patient
from fhir.resources.bundle import BundleEntry

from fhir.resources.identifier import Identifier

from ..patidx.patient_lookup_data import PatientMasterIndexModel, PatientMasterIndexModelDbRecord, PatientMasterIndexLookUpResponse
from ..patidx import patient_lookup_dao
from . import fhir_resources_merge_utils
from . import fhir_utils



def load_patient_identifier(fhir_id: Identifier) -> PatientMasterIndexModel:
    pmidx: PatientMasterIndexModel =PatientMasterIndexModel.construct()
    pmidx.pmidx_id_value = fhir_id.value

    if pmidx.pmidx_id_value is None: # skip identifiers without values
        return None

    pmidx.pmidx_id_type = fhir_utils.identifier_load_identifier_type(fhir_id.type)
    pmidx.pmidx_id_usage = fhir_id.use
    pmidx.pmidx_id_issuer = fhir_utils.identifier_cleanup_issuer(fhir_utils.identifier_load_issuer(fhir_id))
    return pmidx



def collect_patient_info(patient_array_of_bundles, patient_resource_list, patient_primary_ids, patient_secondary_ids) -> dict():
    pmidx_identifiers = {}

    for b in patient_array_of_bundles:
        for entry in b['entry']:
            if entry['resource'].get('resourceType') == 'Patient':
                pat_resource = Patient.parse_obj(entry['resource'])
                for id in pat_resource.identifier:
                    id: Identifier = id
                    pmidx: PatientMasterIndexModel = load_patient_identifier(id)
                    if pmidx is None:
                        continue
                    pmidx_identifiers[pmidx.get_compound_id()] = pmidx
                    if pmidx.is_primary:
                        patient_primary_ids.append(pmidx.get_compound_id())
                    else:
                        patient_secondary_ids.append(pmidx.get_compound_id())
                # Omitt inactive patients
                if pat_resource.active is not None and not pat_resource.active:
                    continue
                patient_resource_list.append(entry['resource'])

    return pmidx_identifiers


async def get_patient_master_idx_bundle_entry(patient_array_of_bundles, tenant_id):
    # Read batch and extract all patients
    patient_resource_list = []
    patient_primary_ids = []

    # TODO: define if secondary ids should be used
    # if we decide to ignore ids such as Driver's license, SSN(etc), then they should be completely omitted from identifiers
    # currently we are not using this list to search for the id.
    # Not sure if we need to exclude secondary keys from being generated at all
    # if secondary key exists in the database without primary key found ,it will result in error
    # TODO: what to do if type of id is not defined at all. Maybe always create a unique patient?
    patient_secondary_ids = []

    identifiers = collect_patient_info(patient_array_of_bundles, patient_resource_list, patient_primary_ids,
                                       patient_secondary_ids)
    if len(patient_resource_list) == 0:
        raise Exception('No patient resources found. Batch is not eligible for conversion')

    # Use primary_ids to search for existing patient
    rows = await patient_lookup_dao.patient_lookup(tenant_id, patient_primary_ids)

    pmidx_db_result = dict()
    master_idx_set = set()
    for r in rows:
        dbmodel: PatientMasterIndexModelDbRecord \
            = PatientMasterIndexModelDbRecord(pmidx_id=r['requested_id'],
                                              pmidx_master_idx=r['pmidx_master_idx'],
                                              pmidx_id_type=r['pmidx_id_type'],
                                              pmidx_id_issuer=r['pmidx_id_issuer'],
                                              pmidx_id_value=r['pmidx_id_value'],
                                              pmidx_id_usage=r['pmidx_id_usage'])
        pmidx_db_result[dbmodel.pmidx_id] = dbmodel
        if dbmodel.pmidx_master_idx is not None:
            master_idx_set.add(dbmodel.pmidx_master_idx)

    if len(master_idx_set) > 1:
        raise Exception('Merge Functionality is not supported')

    master_idx: int = 0
    new_patient_flag = len(master_idx_set) == 0

    if not new_patient_flag:
        master_idx = master_idx_set.pop()

    keys = set(identifiers.keys()) | set(pmidx_db_result.keys())

    for key in keys:
        if key in pmidx_db_result:
            if key in identifiers:
                pmidx_db_result[key].update_from_model(identifiers[key])
        else:
            identifier: PatientMasterIndexModel = identifiers[key]
            dbmodel: PatientMasterIndexModelDbRecord \
                = PatientMasterIndexModelDbRecord(pmidx_id=identifier.get_compound_id())
            pmidx_db_result[key] = dbmodel.update_from_model(identifier)

    rows = await patient_lookup_dao.create_entries(tenant_id, master_idx, 'primary', pmidx_db_result.values())

    # first row contains the assigned master index
    # if it is new_patient_flag then master_idx is new, otherwise
    master_idx = rows[0]['fn_create_patient_entries']
    patient_resource = Patient.parse_obj(
        fhir_resources_merge_utils.deduplicate_patient_list( patient_resource_list))
    patient_resource.id = master_idx
    entry :BundleEntry = fhir_utils.get_new_bundle_entry_put_resource(patient_resource)
    return PatientMasterIndexLookUpResponse(primaryPatientResourceId=master_idx,
                                            primaryPatientResourceEntry=entry.json())