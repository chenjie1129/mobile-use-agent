import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from cloud_phone import VePhoneClient
from control_policy import (
    ConfirmationRequired,
    DESTRUCTIVE_ACTIONS,
    MUTATING_ACTIONS,
    READ_ONLY_ACTIONS,
    RiskLevel,
    authorize_action,
    risk_for_action,
)


@pytest.mark.parametrize(
    "action, expected",
    [
        pytest.param("ListPod", RiskLevel.READ_ONLY, id="P0 read"),
        pytest.param("PowerOnPod", RiskLevel.MUTATING, id="P1 mutation"),
        pytest.param("DeletePod", RiskLevel.DESTRUCTIVE, id="P2 destructive"),
        pytest.param("UnknownFutureAction", RiskLevel.DESTRUCTIVE, id="deny unknown"),
    ],
)
def test_risk_for_action_classifies_actions(action, expected):
    assert risk_for_action(action) is expected


def test_authorize_action_allows_read_without_confirmation():
    assert authorize_action("ListPod") is RiskLevel.READ_ONLY


@pytest.mark.parametrize("action", ["PowerOnPod", "DeletePod", "RunSyncCommand"])
def test_authorize_action_requires_exact_token(action):
    with pytest.raises(ConfirmationRequired) as exc_info:
        authorize_action(action)

    assert exc_info.value.to_dict()["confirmation_token"] == action


def test_authorize_action_accepts_exact_action_token():
    assert authorize_action("PowerOnPod", "PowerOnPod") is RiskLevel.MUTATING


def test_controlled_action_checks_policy_before_transport(monkeypatch):
    client = VePhoneClient("ak", "sk")
    calls = []
    monkeypatch.setattr(
        client,
        "request_action",
        lambda action, **kwargs: calls.append((action, kwargs)) or {"ok": True},
    )

    with pytest.raises(ConfirmationRequired):
        client.controlled_action("DeletePod", {"ProductId": "p", "PodId": "d"})
    assert calls == []

    result = client.controlled_action(
        "DeletePod",
        {"ProductId": "p", "PodId": "d"},
        confirmation_token="DeletePod",
    )
    assert result == {"ok": True}
    assert calls[0][0] == "DeletePod"


def test_every_supported_action_has_an_explicit_risk_classification():
    classified = READ_ONLY_ACTIONS | MUTATING_ACTIONS | DESTRUCTIVE_ACTIONS
    assert set(VePhoneClient.ACTION_VERSIONS) == classified


def test_controlled_action_redacts_signed_urls(monkeypatch):
    client = VePhoneClient("ak", "sk")
    monkeypatch.setattr(
        client,
        "request_action",
        lambda action, **kwargs: {
            "Result": {
                "PreSignedEdgeURL": "https://signed.example/path?token=secret",
                "PodId": "pod-1",
            }
        },
    )

    result = client.controlled_action("GetPreSignedEdgeURL")

    assert result["Result"]["PreSignedEdgeURL"] == "[REDACTED]"
    assert result["Result"]["PodId"] == "pod-1"
