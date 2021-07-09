import uuid

from deepmerge import Merger
from fhir.resources.identifier import Identifier
from fhir.resources.humanname import HumanName

from . import fhir_utils


def merge_objects(obj_1, obj_2):
    mm = Merger([(dict, ['merge'])], ['override'], ['override'])
    result = mm.merge(obj_1, obj_2)
    return result


# Identifiers will be deduplicated based on value and issuer
def cleanup_identifiers(identifiers: list) -> list:
    identifier_set = dict()
    for item in identifiers:
        id: Identifier = Identifier.parse_obj(item)
        if id.value is None:
            identifier_set[uuid.uuid4()] = id
            continue  # we will not be de-duplicating entries without value
        issuer = fhir_utils.identifier_cleanup_issuer(fhir_utils.identifier_load_issuer(id))
        duplicate_key_search = '|' + id.value + '^' + issuer + '|'
        if duplicate_key_search not in identifier_set:
            identifier_set[duplicate_key_search] = id
            continue
        # deduplicate
        identifier_set[duplicate_key_search] = merge_objects(identifier_set[duplicate_key_search], id)
    return list(identifier_set.values())


# HumanName will be deduplicated based on use
def cleanup_human_name(human_names: []) -> []:
    value_set = dict()
    for item in human_names:
        name: HumanName = HumanName.parse_obj(item)
        use = fhir_utils.humanname_load_use(name)
        if use not in value_set:
            value_set[use] = name
            continue
        # deduplicate
        value_set[use] = merge_objects(value_set[use], name)
    return list(value_set.values())


# Assumes that list is sorted (FOR NOW)
def deduplicate_patient_list(resource_list: []):
    if len(resource_list) <= 1:
        return resource_list[0]
    mm = Merger([(dict, ['merge']), (list, ['append'])], ['override'], ['override'])

    rsrc = resource_list[0]
    patient_identifiers = rsrc['identifier']
    patient_names = rsrc['name']
    for i in range(len(resource_list) - 1):
        patient_identifiers = patient_identifiers + resource_list[i + 1]['identifier']
        patient_names = patient_names + resource_list[i + 1]['name']
        rsrc = mm.merge(rsrc, resource_list[i + 1])

    rsrc['identifier'] = cleanup_identifiers(patient_identifiers)
    rsrc['name'] = cleanup_human_name(patient_names)
    return rsrc
