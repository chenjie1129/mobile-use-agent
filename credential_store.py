"""
凭证持久化管理

AK/SK 在首次运行时由用户配置，保存到本地文件:
    ~/.mobile_use_agent/credentials.json

文件权限设为 600 (仅所有者可读写)，后续运行自动加载，无需重复输入。

ProductId / PodId / 用户提示词 不做持久化，每次发起任务时由用户输入。
"""

import json
import os
import sys
import getpass
from pathlib import Path
from typing import Optional, Tuple

# 凭证文件位置: 用户主目录下
CREDENTIALS_DIR = Path.home() / ".mobile_use_agent"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


def _secret_input(prompt: str) -> str:
    """读取敏感输入: 终端下隐藏回显 (getpass), 管道/非交互场景回退普通输入"""
    if sys.stdin.isatty():
        return getpass.getpass(prompt).strip()
    # 管道输入 (CI/脚本): getpass 会阻塞等待 TTY, 回退为普通读取
    return input(prompt).strip()


def has_credentials() -> bool:
    """检查是否已保存凭证"""
    return CREDENTIALS_FILE.exists()


def load_credentials() -> Optional[Tuple[str, str]]:
    """加载已保存的凭证

    Returns:
        (ak, sk) 元组; 未保存或文件损坏时返回 None
    """
    if not CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ak = data.get("ak", "")
        sk = data.get("sk", "")
        if ak and sk:
            return ak, sk
        return None
    except (json.JSONDecodeError, OSError):
        return None


def save_credentials(ak: str, sk: str) -> Path:
    """保存凭证到本地文件

    文件权限设为 600 (仅所有者可读写)。

    Args:
        ak: Access Key ID
        sk: Secret Access Key

    Returns:
        保存的文件路径
    """
    if not ak or not sk:
        raise ValueError("AK/SK 不能为空")

    # 创建目录 (仅所有者可访问)
    CREDENTIALS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)

    data = {"ak": ak, "sk": sk}

    # 写入文件
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # 收紧权限: 600 = 仅所有者可读写
    os.chmod(CREDENTIALS_FILE, 0o600)
    # 目录权限 700
    os.chmod(CREDENTIALS_DIR, 0o700)

    return CREDENTIALS_FILE


def delete_credentials() -> bool:
    """删除已保存的凭证

    Returns:
        是否成功删除 (文件不存在时返回 False)
    """
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        return True
    return False


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


def get_credentials_interactive(force_setup: bool = False) -> Tuple[str, str]:
    """获取凭证: 优先从本地加载, 首次使用(或强制重配)时交互式输入并保存

    Args:
        force_setup: True 表示忽略已保存凭证, 强制重新输入

    Returns:
        (ak, sk) 元组
    """
    # 尝试加载已保存的凭证
    if not force_setup:
        saved = load_credentials()
        if saved:
            ak, sk = saved
            print(f"[凭证] 已加载本地配置: {mask_secret(ak)}")
            print(f"[凭证] 文件位置: {CREDENTIALS_FILE}")
            return ak, sk

    # 首次使用或强制重配: 交互式输入
    if force_setup:
        print("\n--- 重新配置火山引擎凭证 ---")
    else:
        print("\n--- 首次使用: 配置火山引擎凭证 (仅此一次) ---")
        print("凭证将保存到本地, 后续运行自动加载。")

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
        confirm = input("确认保存? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            break
        print("请重新输入。\n")

    # 保存到本地
    try:
        path = save_credentials(ak, sk)
        print(f"\n[成功] 凭证已保存到: {path}")
        print("[提示] 如需重新配置, 运行: python cli.py setup\n")
    except Exception as e:
        print(f"\n[警告] 凭证保存失败 ({e}), 本次会话仍可继续使用")

    return ak, sk
