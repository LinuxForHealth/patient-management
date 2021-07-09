from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.bundle import BundleEntryRequest
from fhir.resources.resource import Resource
from fhir.resources.reference import Reference

from fhir.resources import coding
from fhir.resources.identifier import Identifier
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.humanname import HumanName

import fhir

fhir_terminology_identifier_type_coding_system = 'http://terminology.hl7.org/CodeSystem/v2-0203'

# see https://www.hl7.org/fhir/identifier-registry.html
fhir_identifier_map = {
    'http://hl7.org/fhir/sid/us-ssn': '2.16.840.1.113883.4.1',
    'http://hl7.org/fhir/sid/us-mbi': '2.16.840.1.113883.4.927'
}


# ==============================================================
# FHIR Identifier
# ==============================================================
def identifier_load_identifier_type(cc: CodeableConcept) -> str:
    if cc is None:
        return 'UNSPECIFIED'
    if cc.coding is None:
        return cc.text

    for c in cc.coding:
        c: coding
        if c.system == fhir_terminology_identifier_type_coding_system:
            selected_identifer = c.code
            break
        selected_identifer = c.code  ## assign but keep looking for other type identifiers that might indicate MR
    return selected_identifer


# TODO: unravel all of the variations of the assigning authority
def identifier_load_issuer(fhir_id: Identifier) -> str:
    if fhir_id.assigner is None:
        return fhir_id.system
    if not hasattr(fhir_id.assigner, '__dict__'):
        return fhir_id.assigner
    else:
        return fhir_id.assigner.reference


def identifier_cleanup_issuer(issuer: str):
    if issuer is None:
        return 'NONE'
    if issuer in fhir_identifier_map:
        return fhir_identifier_map[issuer]
    if issuer.startswith('urn:'):
        value_idx = issuer.find(':', 4)
        if value_idx > 0:
            return issuer[value_idx + 1:]
    return issuer


# ==============================================================
# FHIR HumanName
# ==============================================================
def humanname_load_use(hn: HumanName) -> str:
    if hn.use is None:  # defaulting to usual
        return 'usual'
    return hn.use


# ==============================================================
# FHIR Bundle
# ==============================================================
def get_new_bundle() -> Bundle:
    b = Bundle.construct()
    # TODO: determine if Bundle Type should be configurable
    b.type = 'transaction'
    b.entry = []
    return b


def get_new_bundle_entry(request_method_code, request_url, fhir_resource, full_url) -> BundleEntry:
    entry = BundleEntry.construct()
    entry.resource = fhir_resource
    entry.fullUrl = full_url
    # note there is a bug in fhir.resources the validation
    # both fields are required fields, when setting one field the second field is not set and throws validation error
    # as a work around BundleEntryRequest has to be created as json object first
    request_json = {
        'method': request_method_code,
        'url': request_url
    }
    entry.request = BundleEntryRequest.parse_obj(request_json)

    return entry


def get_new_bundle_entry_put_resource(fhir_resource: Resource) -> BundleEntry:
    return get_new_bundle_entry('PUT', fhir_resource.resource_type + '/' + fhir_resource.id, fhir_resource,
                                'urn:id:' + fhir_resource.id)


def get_new_bundle_entry_put_dict_resource(request_method_code, dict_resource: dict) -> BundleEntry:
    bundle_entry_json = {
        'fullUrl': 'urn:id:' + dict_resource['id'],
        'request': {'method': request_method_code, 'url': dict_resource['resourceType'] + '/' + dict_resource['id']},
        'resource': dict_resource
    }
    return BundleEntry.parse_obj(bundle_entry_json)


def get_patient_reference(patient_resource_id) -> Reference:
    patRef: Reference
    patRef = Reference.construct()
    patRef.reference = 'Patient/' + patient_resource_id
    return patRef


def get_resource_reference(rsc) -> Reference:
    rref: Reference
    rref = Reference.construct()
    rref.reference = rsc['resourceType'] + '/' + rsc['id']
    return rref


# resource_map sample {'Encounter/123':'Encounter/123', 'Encounter/ABC' : 'Encounter/123, 'Observation/1' : 'Observation/2'}
# The resource map keeps track of the changes to resource.id that occurred through processing
# Applying resource map to FHIR object includes recursively examine each field in the object looking for references
# if reference exists as key in resource_map, that reference is replaced with the value associated with that key in the resource_map
def apply_resource_map_to_references(rsrc, resource_map):
    # recursive function - end - found fhir.resource.reference.Reference object
    # apply resource map and return
    if (type(rsrc) == fhir.resources.reference.Reference):
        if rsrc.reference in resource_map:
            replaceValue = resource_map[rsrc.reference]
            if replaceValue is not None:
                rsrc.reference = replaceValue
        return
    # recursive function - end - primitive attribute
    if not hasattr(rsrc, '__dict__'):
        return

    for k, v in vars(rsrc).items():
        # lists and dictionaries will call this function again on its content
        if (type(v) == list):
            for item in v:
                apply_resource_map_to_references(item, resource_map)
        if (type(v) == dict):
            for item in v:
                apply_resource_map_to_references(item, resource_map)

        # Reference object - apply map
        if (type(v) == fhir.resources.reference.Reference):
            if v.reference in resource_map:
                replaceValue = resource_map[v.reference]
                if replaceValue is not None:
                    v.reference = replaceValue

    return


# Method to traverse thru each BundleEntry in the bundle
# Calls apply_resource_map_to_references to apply resource map
def apply_reference_map_to_bundle(patbundle, resource_map):
    for item in patbundle.entry:
        apply_resource_map_to_references(item.resource, resource_map)
    return
