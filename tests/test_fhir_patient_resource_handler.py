import pytest
import os

import json

from cdp_patient_mgmt.fhir import fhir_patient_resource_handler

from cdp_patient_mgmt.patidx.patient_lookup_data import PatientMasterIndexModelDbRecord
from cdp_patient_mgmt.patidx.patient_lookup_data import (
    PatientMasterIndexModel,
    PatientMasterIndexModelDbRecord,
)
from deepdiff import DeepDiff

from fhir.resources.identifier import Identifier
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference

_resources_dir = "tests/resources/for_pat_resource_handler/"
_tenant_id = "test_tenant"


def get_py_objects_from_json_file(file_path: str) -> dict:
    with open(file_path, "r") as file:
        result = json.loads(file.read())
    return result


@pytest.fixture
def mock_doa_fixture(mocker):
    # Create simple fixture to mock patient_lookup_doa.py methods to avoid DB access.
    # Note: for now, keep it simple and hardcode the return mock row data. Consider
    # pulling data from the test json/bundle if that would enhance the test.
    #
    # The *_expected_output.json files need to match the pmidx_master_idx used below.
    #
    # The mock return data dictionary must include the dbmodel keys. Example:
    # dbmodel: PatientMasterIndexModelDbRecord = PatientMasterIndexModelDbRecord(
    #  pmidx_id=r["requested_id"],
    #  pmidx_master_idx=r["pmidx_master_idx"],
    #  pmidx_id_type=r["pmidx_id_type"],
    #  pmidx_id_issuer=r["pmidx_id_issuer"],
    #  pmidx_id_value=r["pmidx_id_value"],
    #  pmidx_id_usage=r["pmidx_id_usage"],
    row_dict = {
        "requested_id": "id11",
        # An error occurs if the pmidx_master_idx" is not a numeric string or an integer.
        # It is used as the FHIR resource id (not MRN/PID value).
        # Note: the fhir resource ID can have a non-numeric id.
        "pmidx_master_idx": "11",
        "pmidx_id_type": "idType11",
        "pmidx_id_issuer": "idIssuer11",
        "pmidx_id_value": "idValue11",
        "pmidx_id_usage": "idUsage11",
    }
    return_rows = [row_dict]  # Just one dictionary for now.
    mocker.patch(
        "cdp_patient_mgmt.patidx.patient_lookup_dao.patient_lookup",
        return_value=return_rows,
    )
    # The return value for _dao.create_entries needs to include the key
    # "fn_create_patient_entries".
    row_dict["fn_create_patient_entries"] = row_dict["pmidx_master_idx"]
    mocker.patch(
        "cdp_patient_mgmt.patidx.patient_lookup_dao.create_entries",
        return_value=return_rows,
    )


def test_collect_patient_info():
    pat_batch = get_py_objects_from_json_file(
        _resources_dir + "single_patient_single_id.json"
    )
    patient_resource_list = []
    patient_primary_ids = []
    patient_secondary_ids = []

    fhir_patient_resource_handler.collect_patient_info(
        pat_batch, patient_resource_list, patient_primary_ids, patient_secondary_ids
    )
    assert len(patient_primary_ids) == 1
    assert "PID1234^Organization/A^MR" in patient_primary_ids
    assert len(patient_secondary_ids) == 0


def test_load_patient_identifier():
    fhir_identifier = Identifier()
    fhir_identifier.value = "11"
    fhir_identifier.type = CodeableConcept(text="idType11")
    fhir_identifier.use = "idUsage11"
    fhir_identifier.assigner = Reference(reference="idIssuerAssigner")

    pat_master_index_model: PatientMasterIndexModel = fhir_patient_resource_handler.load_patient_identifier(
        fhir_identifier
    )

    assert fhir_identifier.value == pat_master_index_model.pmidx_id_value
    assert fhir_identifier.type.text == pat_master_index_model.pmidx_id_type
    assert fhir_identifier.use == pat_master_index_model.pmidx_id_usage
    assert fhir_identifier.assigner.reference == pat_master_index_model.pmidx_id_issuer


def test_pat_master_idx_data_primarykey_bool_set_true():
    pmidx_data = PatientMasterIndexModelDbRecord(
        pmidx_id="AA^1^MR",
        pmidx_master_index=3,
        pmidx_id_type="MR",
        pmidx_id_issuer="1",
        pmidx_id_value="AA",
    )
    assert pmidx_data.is_primary()


def test_pat_master_idx_data_primarykey_bool_set_false():
    pmidx_data = PatientMasterIndexModelDbRecord(
        pmidx_id="AA^1^MR",
        pmidx_master_index=3,
        pmidx_id_type="TYPE",
        pmidx_id_issuer="1",
        pmidx_id_value="AA",
    )
    assert not pmidx_data.is_primary()


@pytest.mark.asyncio
async def test_get_patient_master_idx_bundle_entry_single_patient_single_id(
    mock_doa_fixture,
):
    patbatch = get_py_objects_from_json_file(
        _resources_dir + "single_patient_single_id.json"
    )
    result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
        patbatch, _tenant_id
    )
    expected = get_py_objects_from_json_file(
        _resources_dir + "single_patient_single_id_expected_output.json"
    )
    # Normalize "expected" and "result" for DeepDiff compare.
    # "result" is PatientMasterIndexLookUpResponse. "expected" is Python object.
    dd_result = DeepDiff(expected, json.loads(result.json()), ignore_order=True)
    assert dd_result == {}


@pytest.mark.asyncio
async def test_get_patient_master_idx_bundle_entry_single_patient_multi_id(
    mock_doa_fixture,
):
    patbatch = get_py_objects_from_json_file(
        _resources_dir + "single_patient_multi_id.json"
    )
    result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
        patbatch, _tenant_id
    )
    expected = get_py_objects_from_json_file(
        _resources_dir + "single_patient_multi_id_expected_output.json"
    )
    # Normalize "expected" and "result" for DeepDiff compare.
    dd_result = DeepDiff(expected, json.loads(result.json()), ignore_order=True)
    assert dd_result == {}


@pytest.mark.asyncio
async def test_get_patient_master_idx_bundle_entry_multi_bundle_batch(
    mock_doa_fixture,
):
    patbatch = get_py_objects_from_json_file(_resources_dir + "multi_bundle_batch.json")
    result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
        patbatch, _tenant_id
    )
    expected = get_py_objects_from_json_file(
        _resources_dir + "multi_bundle_batch_expected_output.json"
    )
    # Normalize "expected" and "result" for DeepDiff compare.
    dd_result = DeepDiff(expected, json.loads(result.json()), ignore_order=True)
    assert dd_result == {}


@pytest.mark.asyncio
async def test_get_patient_master_idx_bundle_entry_multi_bundle_repeated_values(
    mock_doa_fixture,
):
    patbatch = get_py_objects_from_json_file(
        _resources_dir + "multi_bundle_repeated_values.json"
    )
    result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
        patbatch, _tenant_id
    )
    expected = get_py_objects_from_json_file(
        _resources_dir + "multi_bundle_repeated_values_expected_output.json"
    )
    # Normalize "expected" and "result" for DeepDiff compare.
    dd_result = DeepDiff(expected, json.loads(result.json()), ignore_order=True)
    assert dd_result == {}


@pytest.mark.asyncio
async def test_get_patient_master_idx_bundle_entry_patient_name_multi(
    mock_doa_fixture,
):
    patbatch = get_py_objects_from_json_file(_resources_dir + "patient_name_multi.json")
    result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
        patbatch, _tenant_id
    )
    expected = get_py_objects_from_json_file(
        _resources_dir + "patient_name_multi_expected_output.json"
    )
    # Normalize "expected" and "result" for DeepDiff compare.
    dd_result = DeepDiff(expected, json.loads(result.json()), ignore_order=True)
    assert dd_result == {}
