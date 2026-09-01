import importlib
import json
import sys
import types
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_mobile_use_agent():
    core = types.ModuleType("volcenginesdkcore")
    core.Configuration = object
    core.UniversalApi = object
    core.ApiClient = object
    core.UniversalInfo = object
    core.Flatten = object

    rest = types.ModuleType("volcenginesdkcore.rest")
    rest.ApiException = RuntimeError

    sys.modules.setdefault("volcenginesdkcore", core)
    sys.modules.setdefault("volcenginesdkcore.rest", rest)
    return importlib.import_module("mobile_use_agent")


def test_save_credentials_does_not_write_secrets_to_profile(tmp_path, monkeypatch):
    credential_store = importlib.import_module("credential_store")
    profile = tmp_path / "profile.json"
    monkeypatch.setattr(credential_store, "CREDENTIALS_DIR", tmp_path)
    monkeypatch.setattr(credential_store, "CREDENTIALS_FILE", profile)
    monkeypatch.setattr(
        credential_store,
        "LEGACY_CREDENTIALS_FILE",
        tmp_path / "credentials.json",
    )

    credential_store.save_credentials(
        "test-access-key",
        "test-secret-key",
        product_id="product-1",
        pod_id="pod-1",
    )

    saved = json.loads(profile.read_text(encoding="utf-8"))
    assert "ak" not in saved
    assert "sk" not in saved
    assert saved["product_id"] == "product-1"
    assert saved["pod_id"] == "pod-1"


def test_run_and_wait_uses_requested_timeout_window(monkeypatch):
    module = _load_mobile_use_agent()
    client = module.MobileUseAgentClient.__new__(module.MobileUseAgentClient)
    client.run_agent_task_one_step = lambda **kwargs: {"RunId": "run-1"}
    client.list_agent_run_current_step = lambda run_id: {"Results": []}
    client.get_agent_result = lambda run_id: (_ for _ in ()).throw(
        RuntimeError("still running")
    )

    clock = {"now": 0, "calls": 0}

    def fake_time():
        clock["calls"] += 1
        clock["now"] += 100
        return clock["now"]

    monkeypatch.setattr(module.time, "time", fake_time)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    result = client.run_and_wait(
        run_name="timeout-test",
        pod_id="pod-1",
        product_id="product-1",
        user_prompt="test",
        timeout=1,
        poll_interval=0,
    )

    assert result["RunId"] == "run-1"
    assert clock["calls"] <= 3


def test_run_and_wait_does_not_treat_pending_result_as_terminal(monkeypatch):
    module = _load_mobile_use_agent()
    client = module.MobileUseAgentClient.__new__(module.MobileUseAgentClient)
    client.run_agent_task_one_step = lambda **kwargs: {"RunId": "run-1"}
    poll = {"count": 0}

    def current_step(run_id):
        poll["count"] += 1
        return {
            "Status": 2 if poll["count"] == 1 else 3,
            "Results": [],
        }

    def agent_result(run_id):
        return {
            "Result": {
                "IsSuccess": 0 if poll["count"] == 1 else 1,
            }
        }

    client.list_agent_run_current_step = current_step
    client.get_agent_result = agent_result
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    result = client.run_and_wait(
        run_name="pending-result-test",
        pod_id="pod-1",
        product_id="product-1",
        user_prompt="test",
        timeout=30,
        poll_interval=0,
    )

    assert poll["count"] == 2
    assert result["Result"]["IsSuccess"] == 1
