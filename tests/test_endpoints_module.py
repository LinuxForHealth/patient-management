import pytest
from fastapi import HTTPException
from cdp_patient_mgmt.rest import endpoints_module
from cdp_patient_mgmt.patidx import patient_lookup_data
from typing import Dict
from cdp_minio.wrapper import MinioClientApi
from pydantic.types import Json


def get_test_zip_bytes() -> bytes:
    with open(
        "./tests/resources/for_endpoints_module/fhirBundlePatientMrnPID1234_2Files.zip",
        "rb",
    ) as file:
        zip_bytes: bytes = file.read()
    return zip_bytes


def test_ping_endpoint():
    print("Test ping...")
    response = endpoints_module.ping()


def test_get_bundle_array():
    unzipped_array = endpoints_module.get_bundle_array(get_test_zip_bytes())
    assert len(unzipped_array) == 2
    assert isinstance(unzipped_array[0], Dict)


def test_get_minio_client():
    # Verify no exceptions as well as a value is returned.
    assert endpoints_module.get_minio_client()


def test_verify_tenant_id():
    endpoints_module.verify_tenant_id("some-tenant-id")  # Expect no Exception.

    with pytest.raises(HTTPException):
        endpoints_module.verify_tenant_id(None)  # Expect Exception.

    with pytest.raises(HTTPException):
        endpoints_module.verify_tenant_id("  ")  # Expect Exception.


@pytest.mark.asyncio
async def test_patient_bundle(mocker):
    mocker.patch.object(MinioClientApi, "get_object", return_value=get_test_zip_bytes())

    # Mock fhir_patient_resource_handler.get_patient_master_idx_bundle_entry since
    # postgres DB access is needed.
    mocker_response = patient_lookup_data.PatientMasterIndexLookUpResponse(
        primaryPatientResourceId="dummy_patient_MRN",
        primaryPatientResourceEntry='{"mock patient entry": "bundle"}',
    )
    mocker.patch(
        "cdp_patient_mgmt.fhir.fhir_patient_resource_handler.get_patient_master_idx_bundle_entry",
        return_value=mocker_response,
    )
    response = await endpoints_module.patient_bundle("dummy_storage_id", "dummy_tenant")
    assert response != None
