import os

from whi_caf_lib_configreader import config as configreader


CONFIG_ENV = "WHPA_CDP_PATIENT_MANAGEMENT_SERVICE_CONFIG"
MINIO_SECRETS_ENV = "WHPA_CDP_MINIO_SECRETS"

minio_header = "minio"
minio_required_keys = ["MINIO_ENDPOINT", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"]

_configs = None


def _load_configs():
    global _configs

    config_file_path = os.getenv(CONFIG_ENV, "config/config.ini")
    minio_secrets_folder = os.getenv(MINIO_SECRETS_ENV, "secrets/minio/")

    config = configreader.load_config(
        config_file_path, secrets_dir=[minio_secrets_folder]
    )
    configreader.validate_config(config, minio_header, minio_required_keys)
    _configs = config


def get_config():
    if _configs is None:
        _load_configs()
    return _configs