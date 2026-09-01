"""非敏感配置与环境变量凭证管理。

AK/SK 只从环境变量读取，绝不写入本地文件。配置文件仅保存默认
ProductId/PodId，便于 Agent 在后续运行中复用已选择的设备。
"""

import json
import os
import sys
import getpass
from pathlib import Path
from typing import Optional, Tuple

# 非敏感配置文件位置
CREDENTIALS_DIR = Path.home() / ".mobile_use_agent"
CREDENTIALS_FILE = CREDENTIALS_DIR / "profile.json"
LEGACY_CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
ACCESS_KEY_ENV_NAMES = ("VOLC_ACCESSKEY", "VOLC_ACCESS_KEY")
SECRET_KEY_ENV_NAMES = ("VOLC_SECRETKEY", "VOLC_SECRET_KEY")


def _secret_input(prompt: str) -> str:
    """读取敏感输入: 终端下隐藏回显 (getpass), 管道/非交互场景回退普通输入"""
    if sys.stdin.isatty():
        return getpass.getpass(prompt).strip()
    # 管道输入 (CI/脚本): getpass 会阻塞等待 TTY, 回退为普通读取
    return input(prompt).strip()


def _read_file() -> dict:
    """读取非敏感配置文件，不存在或损坏时返回空字典。"""
    if not CREDENTIALS_FILE.exists():
        return {}
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_file(data: dict) -> Path:
    """写入凭证文件, 权限 600 / 目录 700"""
    CREDENTIALS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(CREDENTIALS_FILE, 0o600)
    os.chmod(CREDENTIALS_DIR, 0o700)
    return CREDENTIALS_FILE


def _migrate_legacy_profile() -> None:
    """Remove legacy plaintext secrets while preserving non-sensitive IDs."""
    if not LEGACY_CREDENTIALS_FILE.exists():
        return
    try:
        with open(LEGACY_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            legacy = json.load(f)
    except (json.JSONDecodeError, OSError):
        legacy = {}
    safe = _read_file()
    for key in ("product_id", "pod_id"):
        if legacy.get(key) and not safe.get(key):
            safe[key] = legacy[key]
    if safe:
        _write_file(safe)
    LEGACY_CREDENTIALS_FILE.unlink(missing_ok=True)


def has_credentials() -> bool:
    """检查当前进程是否已通过环境变量获得完整凭证。"""
    return load_credentials() is not None


def load_credentials() -> Optional[Tuple[str, str]]:
    """从环境变量加载凭证。

    Returns:
        (ak, sk) 元组；环境变量未完整设置时返回 None。
    """
    ak = next(
        (
            os.environ.get(name, "")
            for name in ACCESS_KEY_ENV_NAMES
            if os.environ.get(name)
        ),
        "",
    )
    sk = next(
        (
            os.environ.get(name, "")
            for name in SECRET_KEY_ENV_NAMES
            if os.environ.get(name)
        ),
        "",
    )
    if ak and sk:
        _migrate_legacy_profile()
        return ak, sk
    return None


def load_profile() -> dict:
    """加载完整配置档案

    Returns:
        dict: {ak, sk, product_id, pod_id}。AK/SK 来自环境变量。
    """
    data = _read_file()
    credentials = load_credentials() or ("", "")
    return {
        "ak": credentials[0],
        "sk": credentials[1],
        "product_id": data.get("product_id", ""),
        "pod_id": data.get("pod_id", ""),
    }


def save_credentials(
    ak: str,
    sk: str,
    product_id: str = "",
    pod_id: str = "",
) -> Path:
    """仅保存非敏感设备配置，AK/SK 不落盘。

    Args:
        ak: Access Key ID
        sk: Secret Access Key
        product_id: 默认云手机业务 ID (可选, 留空不保存)
        pod_id: 默认云手机实例 ID (可选, 留空不保存)

    Returns:
        非敏感配置文件路径
    """
    if not ak or not sk:
        raise ValueError("AK/SK 不能为空")

    data = _read_file()
    data.pop("ak", None)
    data.pop("sk", None)
    data["credential_source"] = "environment"
    if product_id:
        data["product_id"] = product_id
    if pod_id:
        data["pod_id"] = pod_id

    path = _write_file(data)
    if LEGACY_CREDENTIALS_FILE != path and LEGACY_CREDENTIALS_FILE.exists():
        LEGACY_CREDENTIALS_FILE.unlink()
    return path


def set_default_device(product_id: str, pod_id: str) -> Path:
    """保存默认云手机 (不修改 AK/SK)

    Args:
        product_id: 云手机业务 ID
        pod_id: 云手机实例 ID

    Returns:
        保存的文件路径
    """
    if not product_id or not pod_id:
        raise ValueError("ProductId/PodId 不能为空")
    data = _read_file()
    data["product_id"] = product_id
    data["pod_id"] = pod_id
    return _write_file(data)


def clear_default_device() -> Path:
    """清除保存的默认云手机 (保留 AK/SK)"""
    data = _read_file()
    data.pop("product_id", None)
    data.pop("pod_id", None)
    return _write_file(data)


def get_default_device() -> Tuple[str, str]:
    """获取保存的默认云手机

    Returns:
        (product_id, pod_id), 未配置时均为空字符串
    """
    data = _read_file()
    return data.get("product_id", ""), data.get("pod_id", "")


def delete_credentials() -> bool:
    """删除非敏感配置和旧版明文凭证文件。

    Returns:
        是否成功删除 (文件不存在时返回 False)
    """
    removed = False
    for path in (CREDENTIALS_FILE, LEGACY_CREDENTIALS_FILE):
        if path.exists():
            path.unlink()
            removed = True
    return removed


def mask_secret(secret: str, show_prefix: int = 4, show_suffix: int = 4) -> str:
    """脱敏展示密钥

    Args:
        secret: 原始密钥
        show_prefix: 展示前缀字符数
        show_suffix: 展示后缀字符数

    Returns:
        脱敏后的字符串, 如 "AKLT****abcd"
    """
    if not secret:
        return "(空)"

    if len(secret) <= show_prefix + show_suffix:
        return "*" * len(secret)

    return (
        secret[:show_prefix]
        + "*" * 8
        + secret[-show_suffix:]
    )


def mask_id(id_str: str, show_head: int = 6, show_tail: int = 4) -> str:
    """脱敏展示长 ID (ProductId/PodId 等)

    Args:
        id_str: 原始 ID
        show_head: 展示头部字符数
        show_tail: 展示尾部字符数

    Returns:
        脱敏后的字符串, 如 "prod-1f3a****9c2e"; 短 ID 直接返回
    """
    if not id_str:
        return "(未设置)"
    if len(id_str) <= show_head + show_tail:
        return id_str
    return f"{id_str[:show_head]}****{id_str[-show_tail:]}"


def get_credentials_interactive(force_setup: bool = False) -> Tuple[str, str]:
    """获取凭证：优先读取环境变量，交互输入只在当前进程使用。

    Args:
        force_setup: True 表示忽略环境变量并强制重新输入

    Returns:
        (ak, sk) 元组
    """
    # 尝试从环境变量加载凭证。
    if not force_setup:
        loaded = load_credentials()
        if loaded:
            ak, sk = loaded
            print(f"[凭证] 已从环境变量加载: {mask_secret(ak)}")
            return ak, sk

    # 首次使用或强制重配: 交互式输入
    if force_setup:
        print("\n--- 临时输入火山引擎凭证 ---")
    else:
        print("\n--- 首次使用: 输入火山引擎凭证 ---")
        print("AK/SK 只在当前进程使用，不会写入磁盘。")

    print("获取方式: 火山引擎控制台 -> 右上角头像 -> 访问密钥\n")

    while True:
        ak = _secret_input("请输入 AK (Access Key ID): ")
        if not ak:
            print("[错误] AK 不能为空, 请重新输入")
            continue

        sk = _secret_input("请输入 SK (Secret Access Key): ")
        if not sk:
            print("[错误] SK 不能为空, 请重新输入")
            continue

        # 确认
        print(f"\nAK: {mask_secret(ak)}")
        confirm = input("确认用于本次会话? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            break
        print("请重新输入。\n")

    print("\n[安全] AK/SK 未写入磁盘。长期使用请通过凭证代理注入环境变量：")
    print("       VOLC_ACCESSKEY / VOLC_SECRETKEY")
    save_credentials(ak, sk)

    return ak, sk
