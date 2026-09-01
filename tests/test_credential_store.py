import importlib
import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

credential_store = importlib.import_module("credential_store")


def _use_temp_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(credential_store, "CREDENTIALS_DIR", tmp_path)
    monkeypatch.setattr(
        credential_store,
        "CREDENTIALS_FILE",
        tmp_path / "profile.json",
    )
    monkeypatch.setattr(
        credential_store,
        "LEGACY_CREDENTIALS_FILE",
        tmp_path / "credentials.json",
    )


def test_load_credentials_prefers_standard_environment(monkeypatch, tmp_path):
    _use_temp_profile(monkeypatch, tmp_path)
    monkeypatch.setenv("VOLC_ACCESSKEY", "ak-standard")
    monkeypatch.setenv("VOLC_SECRETKEY", "sk-standard")
    monkeypatch.setenv("VOLC_ACCESS_KEY", "ak-alias")
    monkeypatch.setenv("VOLC_SECRET_KEY", "sk-alias")

    assert credential_store.load_credentials() == ("ak-standard", "sk-standard")


def test_load_credentials_supports_acep_environment_aliases(monkeypatch, tmp_path):
    _use_temp_profile(monkeypatch, tmp_path)
    monkeypatch.delenv("VOLC_ACCESSKEY", raising=False)
    monkeypatch.delenv("VOLC_SECRETKEY", raising=False)
    monkeypatch.setenv("VOLC_ACCESS_KEY", "ak-alias")
    monkeypatch.setenv("VOLC_SECRET_KEY", "sk-alias")

    assert credential_store.load_credentials() == ("ak-alias", "sk-alias")


def test_legacy_file_is_scrubbed_and_device_ids_are_migrated(monkeypatch, tmp_path):
    _use_temp_profile(monkeypatch, tmp_path)
    monkeypatch.setenv("VOLC_ACCESSKEY", "replacement-ak")
    monkeypatch.setenv("VOLC_SECRETKEY", "replacement-sk")
    monkeypatch.delenv("VOLC_ACCESS_KEY", raising=False)
    monkeypatch.delenv("VOLC_SECRET_KEY", raising=False)
    legacy = tmp_path / "credentials.json"
    legacy.write_text(
        json.dumps(
            {
                "ak": "legacy-ak",
                "sk": "legacy-sk",
                "product_id": "product-1",
                "pod_id": "pod-1",
            }
        ),
        encoding="utf-8",
    )

    assert credential_store.load_credentials() == ("replacement-ak", "replacement-sk")
    assert legacy.exists() is False
    profile = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert profile == {"product_id": "product-1", "pod_id": "pod-1"}


def test_legacy_file_is_not_deleted_before_replacement_credentials_exist(
    monkeypatch,
    tmp_path,
):
    _use_temp_profile(monkeypatch, tmp_path)
    for name in (
        "VOLC_ACCESSKEY",
        "VOLC_SECRETKEY",
        "VOLC_ACCESS_KEY",
        "VOLC_SECRET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    legacy = tmp_path / "credentials.json"
    legacy.write_text(
        json.dumps({"ak": "legacy-ak", "sk": "legacy-sk"}),
        encoding="utf-8",
    )

    assert credential_store.load_credentials() is None
    assert legacy.exists() is True
