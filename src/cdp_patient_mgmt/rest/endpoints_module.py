"""
Purpose: Patient Management Service rest API endpoints associated with the project.yaml file.
"""

from fastapi import HTTPException
from ..util import service_logger, config
import json
import os

from cdp_minio.wrapper import MinioClientApi
from zipfile import ZipFile
from io import BytesIO
from ..fhir import fhir_patient_resource_handler

logger = service_logger.get_logger(__name__)
cfg = config.get_config()


def verify_tenant_id(tenant_id: str):
    """ Utility to verify tenant id provide and throw exception if not. """
    if tenant_id == None or tenant_id.strip() == "":
        logger.error("'tenant-id' header not provided.")
        raise HTTPException(
            status_code=412, detail="The 'tenant-id' request header is required."
        )


def get_minio_client() -> MinioClientApi:
    # TODO: Change to recommended way to handle secrets if not done via envirnment variables at deploy time.
    mio_ep: str = cfg["minio"]["MINIO_ENDPOINT"]
    mio_key: str = cfg["minio"]["MINIO_ROOT_USER"]
    mio_pw: str = cfg["minio"]["MINIO_ROOT_PASSWORD"]
    if not mio_ep or not mio_key or not mio_pw:
        logger.error("MinIO environment not configured: mio_ep = " + mio_ep)
        raise HTTPException(
            status_code=500, detail="MinIO storage not propertly configured."
        )
    return MinioClientApi(mio_ep, mio_key, mio_pw)


def get_bundle_array(zipped_bundles: bytes) -> list:
    """ Return the list of string patient bundles from the input zipped data. """
    logger.info("Extracting the patient's bundles from the zip object...")
    zf_object = ZipFile(BytesIO(zipped_bundles))
    # Extract the bundles from the zip object and decode the bytes to string.
    string_bundles = list()
    for item in zf_object.filelist:
        try:
            bundle_bytes = zf_object.read(item)
            bundle = json.loads(bundle_bytes.decode("utf-8"))
        except:
            logger.exception(
                "Failed to retrieve zip compressed item: {0}.".format(str(item))
            )
            continue
        string_bundles.append(bundle)
    return string_bundles


# Simple API to verify the service is running.
def ping():
    return {"Pong - the patient management service is running."}


# Note: FastAPI will convert the dashes/hyphens to underscore since a dash is not in
# python variable names, thus, use "tenant_id" for the header "tenant-id"
async def patient_bundle(patbatch_storage_id: str, tenant_id: str):
    """
    This endpoint returns a FHIR patient bundle.
    """
    verify_tenant_id(tenant_id)

    try:
        logger.info("Process patient_bundle request.")
        logger.info("tenant_id=" + tenant_id)
        logger.info("patbatch_storage_id=" + patbatch_storage_id)

        # Get the patient's FHIR bundle or bundles that need modification.
        minio_client = get_minio_client()
        logger.info("got minio_client()")
        pat_zipped_bundles = await minio_client.get_object(
            tenant_id, patbatch_storage_id
        )
        logger.info("got pat_zipped_bundles")
        pat_bundles = get_bundle_array(pat_zipped_bundles)
        logger.info("got pat_bundles")
        ##############################
        # Patient Resource Management logic
        result = await fhir_patient_resource_handler.get_patient_master_idx_bundle_entry(
            pat_bundles, tenant_id
        )
        print("RESULT: ", result.json())
        #
        ##############################
    except Exception as e:
        logger.error("Unexcepted error", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error. " + str(e))

    # Note: FASTAPI maps Python objects to json, thus json.dumps() is not needed.
    return result


if __name__ == "__main__":
    pass
