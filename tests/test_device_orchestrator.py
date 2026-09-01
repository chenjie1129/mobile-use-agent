import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from device_orchestrator import DeviceOrchestrator


class FakeCloudPhoneClient:
    def __init__(self, products=None, pods=None):
        self.products = products or []
        self.pods = pods or []
        self.calls = []

    def list_products(self, **kwargs):
        self.calls.append(("list_products", kwargs))
        return {"Result": {"ProductList": self.products}}

    def list_pods(self, **kwargs):
        self.calls.append(("list_pods", kwargs))
        return {"Result": {"PodList": self.pods}}

    def list_pod_resources(self, **kwargs):
        return {"Result": {"Rows": [{"ConfigurationCode": "g3"}]}}

    def list_configurations(self, **kwargs):
        return {"Result": {"Rows": [{"ConfigurationCode": "g3"}]}}

    def list_dcs(self, **kwargs):
        return {"Result": {"Rows": [{"Dc": "dc-1"}]}}

    def power_on_pod(self, pod_id, product_id):
        self.calls.append(("power_on_pod", product_id, pod_id))
        return {"TaskId": "task-power"}

    def create_pod_one_step(self, **kwargs):
        self.calls.append(("create_pod_one_step", kwargs))
        return {"PodId": "pod-new", "TaskId": "task-create"}


def test_resolve_returns_console_action_when_product_missing():
    client = FakeCloudPhoneClient()

    result = DeviceOrchestrator(client).resolve()

    assert result.status == "product_required"
    assert result.next_action["type"] == "open_console"
    assert client.calls == [("list_products", {"count": 100})]


def test_resolve_auto_selects_single_ready_device():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1", "ProductName": "mua"}],
        pods=[{"PodId": "pod-1", "Online": 1}],
    )

    result = DeviceOrchestrator(client).resolve()

    assert result.ready is True
    assert result.product_id == "product-1"
    assert result.pod_id == "pod-1"


def test_resolve_returns_product_candidates_when_ambiguous():
    client = FakeCloudPhoneClient(
        products=[
            {"ProductId": "product-1"},
            {"ProductId": "product-2"},
        ]
    )

    result = DeviceOrchestrator(client).resolve()

    assert result.status == "product_selection_required"
    assert [item["id"] for item in result.candidates] == [
        "product-1",
        "product-2",
    ]


def test_resolve_discovers_capacity_when_pod_missing():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[],
    )

    result = DeviceOrchestrator(client).resolve()

    assert result.status == "pod_creation_required"
    assert result.next_action["confirmation_token"] == "CreatePodOneStep"
    assert set(result.details) == {"resources", "configurations", "dcs"}


def test_resolve_requires_confirmation_before_create():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[],
    )

    result = DeviceOrchestrator(client).resolve(
        create_params={
            "configuration_code": "g3",
            "dc": "dc-1",
            "resource_type": 200,
        }
    )

    assert result.status == "confirmation_required"
    assert not any(call[0] == "create_pod_one_step" for call in client.calls)


def test_resolve_requests_missing_create_parameters_before_confirmation():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[],
    )

    result = DeviceOrchestrator(client).resolve(
        create_params={"configuration_code": "g3"}
    )

    assert result.status == "pod_configuration_required"
    assert result.next_action["required_fields"] == ["dc", "resource_type"]


def test_resolve_creates_pod_after_exact_confirmation():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[],
    )

    result = DeviceOrchestrator(client).resolve(
        create_params={
            "configuration_code": "g3",
            "dc": "dc-1",
            "resource_type": 200,
        },
        confirmation_token="CreatePodOneStep",
    )

    assert result.status == "provisioning"
    assert result.pod_id == "pod-new"
    assert any(call[0] == "create_pod_one_step" for call in client.calls)


def test_resolve_requires_confirmation_before_power_on():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[{"PodId": "pod-1", "Online": 2}],
    )

    result = DeviceOrchestrator(client).resolve(auto_power_on=True)

    assert result.status == "confirmation_required"
    assert not any(call[0] == "power_on_pod" for call in client.calls)


def test_resolve_rejects_explicit_pod_outside_product():
    client = FakeCloudPhoneClient(
        products=[{"ProductId": "product-1"}],
        pods=[{"PodId": "pod-1", "Online": 1}],
    )

    result = DeviceOrchestrator(client).resolve(
        product_id="product-1",
        pod_id="pod-missing",
    )

    assert result.status == "pod_not_found"
    assert result.next_action == {"type": "select_pod"}
