import argparse
import importlib
import json
import sys
import types
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_cli():
    if "volcenginesdkcore" not in sys.modules:
        core = types.ModuleType("volcenginesdkcore")
        core.Configuration = object
        core.UniversalApi = object
        core.ApiClient = object
        core.UniversalInfo = object
        core.Flatten = object
        rest = types.ModuleType("volcenginesdkcore.rest")
        rest.ApiException = RuntimeError
        sys.modules["volcenginesdkcore"] = core
        sys.modules["volcenginesdkcore.rest"] = rest
    return importlib.import_module("cli")


class FakeMuaClient:
    def run_agent_task_one_step(self, **kwargs):
        return {"RunId": "run-1", "ThreadId": "thread-1"}

    def list_agent_run_current_step(self, run_id):
        return {
            "Results": [
                {
                    "Action": "click",
                    "StepResult": {"IsSuccess": True},
                }
            ]
        }

    def get_agent_result(self, run_id):
        return {"Result": {"IsSuccess": 1, "Content": "done"}}


def test_run_and_wait_agent_json_emits_jsonl(monkeypatch, capsys):
    cli = _load_cli()
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)

    cli.run_and_wait_agent_json(
        FakeMuaClient(),
        run_name="test",
        product_id="product-1",
        pod_id="pod-1",
        user_prompt="inspect",
        timeout=10,
    )

    events = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.strip()
    ]
    assert [event["event"] for event in events] == [
        "started",
        "progress",
        "result",
    ]
    assert all(event["run_id"] == "run-1" for event in events)


def test_noninteractive_run_without_prompt_returns_machine_readable_status(capsys):
    cli = _load_cli()
    args = argparse.Namespace(
        prompt="",
        product_id="",
        pod_id="",
        no_interactive=True,
        agent_json=True,
    )

    cli.cmd_run_one_step(FakeMuaClient(), args)

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "prompt_required"
