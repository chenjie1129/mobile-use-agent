"""云手机控制面动作分级与确认门禁。"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class RiskLevel(str, Enum):
    READ_ONLY = "P0"
    MUTATING = "P1"
    DESTRUCTIVE = "P2"


READ_ONLY_ACTIONS = {
    "ListOperableProduct",
    "ListPod",
    "DetailPod",
    "GetPodMetric",
    "GetPodProperty",
    "GetPodAppList",
    "ListApp",
    "DetailApp",
    "ListAppVersionDeploy",
    "GetAppCrashLog",
    "ListTask",
    "GetTaskInfo",
    "ListDc",
    "ListPodResource",
    "ListPodResourceSet",
    "GetProductResource",
    "ListConfiguration",
    "ListInstanceConfigurationSpec",
    "ListPhoneTemplate",
    "GetPhoneTemplate",
    "ListHost",
    "DetailHost",
    "ListImageResource",
    "ListAOSPImage",
    "GetImagePreheating",
    "GetDcBandwidthDailyPeak",
    "ListDisplayLayoutMini",
    "DetailDisplayLayoutMini",
    "ListTag",
    "ListPortMappingRule",
    "DetailPortMappingRule",
    "ListDNSRule",
    "DetailDNSRule",
    "ListCustomRoute",
    "GetProxy",
    "ListBackupData",
    "GetPreSignedEdgeURL",
}

MUTATING_ACTIONS = {
    "PowerOnPod",
    "PowerOffPod",
    "RebootPod",
    "InstallApp",
    "InstallApps",
    "AutoInstallApp",
    "LaunchApp",
    "LaunchApps",
    "CloseApp",
    "UninstallApp",
    "StartRecording",
    "StopRecording",
    "StartScreenShot",
    "BatchScreenShot",
    "StopScreenShot",
    "SetProxy",
    "BackupPod",
    "CancelBackupPod",
    "RestorePod",
    "CancelRestorePod",
    "BackupData",
    "RestoreData",
    "PodMute",
    "PodStop",
    "UpdatePodProperty",
    "CreateTag",
    "UpdateTag",
    "AttachTag",
}

DESTRUCTIVE_ACTIONS = {
    "CreatePod",
    "CreatePodOneStep",
    "DeletePod",
    "ResetPod",
    "UpdatePod",
    "MigratePod",
    "PodDataTransfer",
    "PodDataDelete",
    "PodAdb",
    "RunCommand",
    "RunSyncCommand",
    "PushFile",
    "PullFile",
    "DeleteBackupData",
    "SubscribeResourceAuto",
    "RenewResourceAuto",
    "UnsubscribeHostResource",
    "UpdatePodResourceApplyNum",
    "UpdateProductResource",
    "UpdateHost",
    "RebootHost",
    "ResetHost",
    "AddPhoneTemplate",
    "UpdatePhoneTemplate",
    "RemovePhoneTemplate",
    "CreateImageOneStep",
    "BuildAOSPImage",
    "UpdateAOSPImage",
    "DeleteAOSPImage",
    "CreateDisplayLayoutMini",
    "DeleteDisplayLayout",
    "UploadApp",
    "UpdateApp",
    "DeleteApp",
    "DeleteAppVersion",
    "BanUser",
    "DeleteTag",
    "CreatePortMappingRule",
    "BindPortMappingRule",
    "UnbindPortMappingRule",
    "CreateDNSRule",
    "UpdateDNSRule",
    "DeleteDNSRule",
    "AddCustomRoute",
    "UpdateCustomRoute",
    "DeleteCustomRoute",
}


@dataclass(frozen=True)
class ConfirmationRequired(RuntimeError):
    action: str
    risk: RiskLevel

    def __str__(self) -> str:
        return (
            f"{self.action} is a {self.risk.value} state-changing action; "
            f"repeat with confirmation token '{self.action}'"
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "status": "confirmation_required",
            "action": self.action,
            "risk": self.risk.value,
            "confirmation_token": self.action,
        }


def risk_for_action(action: str) -> RiskLevel:
    if action in READ_ONLY_ACTIONS:
        return RiskLevel.READ_ONLY
    if action in MUTATING_ACTIONS:
        return RiskLevel.MUTATING
    return RiskLevel.DESTRUCTIVE


def authorize_action(action: str, confirmation_token: str = "") -> RiskLevel:
    """Allow reads and require an exact, action-bound token for writes."""
    risk = risk_for_action(action)
    if risk is not RiskLevel.READ_ONLY and confirmation_token != action:
        raise ConfirmationRequired(action=action, risk=risk)
    return risk
