"""Agent-friendly Product/Pod discovery and preparation workflow."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from control_policy import ConfirmationRequired, authorize_action


PRODUCT_LIST_KEYS = ("ProductList", "Products", "Rows", "Row", "Items")
POD_LIST_KEYS = ("PodList", "Pods", "Rows", "Row", "Items")
PRODUCT_ID_KEYS = ("ProductId", "ProductID", "product_id")
POD_ID_KEYS = ("PodId", "PodID", "pod_id")
ONLINE_KEYS = ("Online", "Status", "PodStatus", "InstanceStatus")
READY_VALUES = {True, 1, "1", "online", "running", "ready", "started"}


@dataclass
class DeviceResolution:
    status: str
    product_id: str = ""
    pod_id: str = ""
    message: str = ""
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    next_action: Optional[Dict[str, Any]] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.status == "ready"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _first_value(record: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _extract_records(
    payload: Any,
    list_keys: Iterable[str],
    id_keys: Iterable[str],
) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in list_keys:
            value = payload.get(key)
            if isinstance(value, list):
                records = [item for item in value if isinstance(item, dict)]
                if records:
                    return records
        if _first_value(payload, id_keys):
            return [payload]
        for value in payload.values():
            records = _extract_records(value, list_keys, id_keys)
            if records:
                return records
    elif isinstance(payload, list):
        records = [item for item in payload if isinstance(item, dict)]
        if records and any(_first_value(item, id_keys) for item in records):
            return records
        for value in payload:
            nested = _extract_records(value, list_keys, id_keys)
            if nested:
                return nested
    return []


def _public_candidate(record: Dict[str, Any], id_keys: Iterable[str]) -> Dict[str, Any]:
    candidate = {"id": str(_first_value(record, id_keys) or "")}
    for source, target in (
        ("ProductName", "name"),
        ("PodName", "name"),
        ("Online", "online"),
        ("Status", "status"),
        ("PodStatus", "status"),
        ("Dc", "dc"),
        ("ConfigurationCode", "configuration_code"),
    ):
        if source in record:
            candidate[target] = record[source]
    return candidate


def _pod_is_ready(record: Dict[str, Any]) -> bool:
    state = _first_value(record, ONLINE_KEYS)
    if state is None:
        return True
    if isinstance(state, str):
        state = state.strip().lower()
    return state in READY_VALUES


class DeviceOrchestrator:
    """Resolve an executable cloud phone without hiding decisions from the Agent."""

    def __init__(self, cloud_phone_client):
        self.client = cloud_phone_client

    def resolve(
        self,
        product_id: str = "",
        pod_id: str = "",
        *,
        auto_power_on: bool = False,
        confirmation_token: str = "",
        create_params: Optional[Dict[str, Any]] = None,
    ) -> DeviceResolution:
        if not product_id:
            product_response = self.client.list_products(count=100)
            products = _extract_records(
                product_response, PRODUCT_LIST_KEYS, PRODUCT_ID_KEYS
            )
            if not products:
                return DeviceResolution(
                    status="product_required",
                    message="当前账号没有可用的 MUA 业务，请先在控制台创建业务。",
                    next_action={
                        "type": "open_console",
                        "url": "https://console.volcengine.com/ACEP/Business/6",
                        "reason": "创建业务会涉及服务开通和协议确认，必须由用户完成",
                    },
                )
            if len(products) > 1:
                return DeviceResolution(
                    status="product_selection_required",
                    message="发现多个 MUA 业务，需要明确选择 ProductId。",
                    candidates=[
                        _public_candidate(item, PRODUCT_ID_KEYS) for item in products
                    ],
                    next_action={"type": "select_product"},
                )
            product_id = str(_first_value(products[0], PRODUCT_ID_KEYS))

        pod_response = self.client.list_pods(
            product_id=product_id,
            max_results=100,
        )
        pods = _extract_records(pod_response, POD_LIST_KEYS, POD_ID_KEYS)
        if not pods:
            if create_params is None:
                return self._pod_creation_required(product_id)
            return self._create_pod(
                product_id=product_id,
                create_params=create_params,
                confirmation_token=confirmation_token,
            )

        if not pod_id:
            ready_pods = [item for item in pods if _pod_is_ready(item)]
            if len(ready_pods) == 1:
                pod_id = str(_first_value(ready_pods[0], POD_ID_KEYS))
            elif len(ready_pods) > 1:
                return DeviceResolution(
                    status="pod_selection_required",
                    product_id=product_id,
                    message="发现多个运行中的云手机，需要明确选择 PodId。",
                    candidates=[
                        _public_candidate(item, POD_ID_KEYS) for item in ready_pods
                    ],
                    next_action={"type": "select_pod"},
                )
            elif len(pods) == 1:
                pod_id = str(_first_value(pods[0], POD_ID_KEYS))
            else:
                return DeviceResolution(
                    status="pod_selection_required",
                    product_id=product_id,
                    message="没有唯一可选的运行中云手机。",
                    candidates=[
                        _public_candidate(item, POD_ID_KEYS) for item in pods
                    ],
                    next_action={"type": "select_pod"},
                )

        selected = next(
            (
                item
                for item in pods
                if str(_first_value(item, POD_ID_KEYS)) == str(pod_id)
            ),
            None,
        )
        if selected is None:
            return DeviceResolution(
                status="pod_not_found",
                product_id=product_id,
                pod_id=pod_id,
                message="指定的 PodId 不属于当前业务或当前不可见。",
                candidates=[
                    _public_candidate(item, POD_ID_KEYS) for item in pods
                ],
                next_action={"type": "select_pod"},
            )
        if selected is not None and not _pod_is_ready(selected):
            if not auto_power_on:
                return DeviceResolution(
                    status="power_on_required",
                    product_id=product_id,
                    pod_id=pod_id,
                    message="已找到云手机，但它未处于运行状态。",
                    next_action={
                        "type": "confirm_action",
                        "action": "PowerOnPod",
                        "confirmation_token": "PowerOnPod",
                    },
                )
            try:
                authorize_action("PowerOnPod", confirmation_token)
            except ConfirmationRequired as exc:
                return DeviceResolution(
                    status="confirmation_required",
                    product_id=product_id,
                    pod_id=pod_id,
                    message=str(exc),
                    next_action=exc.to_dict(),
                )
            self.client.power_on_pod(pod_id, product_id=product_id)
            return DeviceResolution(
                status="provisioning",
                product_id=product_id,
                pod_id=pod_id,
                message="开机请求已提交，请稍后再次解析设备状态。",
            )

        return DeviceResolution("ready", product_id, pod_id, "设备已就绪")

    def _pod_creation_required(self, product_id: str) -> DeviceResolution:
        details = {
            "resources": self.client.list_pod_resources(product_id=product_id),
            "configurations": self.client.list_configurations(product_id=product_id),
            "dcs": self.client.list_dcs(product_id=product_id),
        }
        return DeviceResolution(
            status="pod_creation_required",
            product_id=product_id,
            message="业务下没有云手机实例；请从可用资源中选择规格和机房。",
            next_action={
                "type": "confirm_action",
                "action": "CreatePodOneStep",
                "required_fields": [
                    "configuration_code",
                    "dc",
                    "resource_type",
                ],
                "confirmation_token": "CreatePodOneStep",
            },
            details=details,
        )

    def _create_pod(
        self,
        product_id: str,
        create_params: Dict[str, Any],
        confirmation_token: str,
    ) -> DeviceResolution:
        required = ("configuration_code", "dc", "resource_type")
        missing = [name for name in required if not create_params.get(name)]
        if missing:
            return DeviceResolution(
                status="pod_configuration_required",
                product_id=product_id,
                message=f"创建云手机缺少参数: {', '.join(missing)}",
                next_action={
                    "type": "provide_parameters",
                    "action": "CreatePodOneStep",
                    "required_fields": missing,
                },
            )

        try:
            authorize_action("CreatePodOneStep", confirmation_token)
        except ConfirmationRequired as exc:
            return DeviceResolution(
                status="confirmation_required",
                product_id=product_id,
                message=str(exc),
                next_action=exc.to_dict(),
            )

        response = self.client.create_pod_one_step(
            product_id=product_id,
            configuration_code=create_params["configuration_code"],
            dc=create_params["dc"],
            resource_type=int(create_params["resource_type"]),
            app_list=create_params.get("app_list", []),
            pod_name=create_params.get("pod_name"),
            image_id=create_params.get("image_id"),
            phone_template_id=create_params.get("phone_template_id"),
            use_phone_template=create_params.get("use_phone_template"),
        )
        pods = _extract_records(response, POD_LIST_KEYS, POD_ID_KEYS)
        new_pod_id = ""
        if pods:
            new_pod_id = str(_first_value(pods[0], POD_ID_KEYS) or "")
        if not new_pod_id and isinstance(response, dict):
            new_pod_id = str(_first_value(response, POD_ID_KEYS) or "")
        return DeviceResolution(
            status="provisioning",
            product_id=product_id,
            pod_id=new_pod_id,
            message="云手机创建请求已提交，实例就绪后可发起 MUA 任务。",
            details={"create_response": response},
        )
