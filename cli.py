#!/usr/bin/env python3
"""
Mobile Use Agent - 交互式 CLI

凭证策略:
  - AK/SK: 首次运行时配置, 保存到本地 (~/.mobile_use_agent/credentials.json)
           后续运行自动加载, 无需重复输入
  - ProductId / PodId / 用户提示词: 每次发起任务时由用户输入

用法:
  # 交互式模式 (首次运行会引导配置 AK/SK)
  python cli.py

  # 重新配置凭证
  python cli.py setup

  # 查看当前凭证状态
  python cli.py whoami

  # 一键运行任务 (每次输入 ProductId/PodId/提示词)
  python cli.py run

  # 命令行直接传参 (跳过交互)
  python cli.py run --product-id PID --pod-id POD --prompt "打开微信"

  # 查询任务状态 / 结果 / 取消 / 列表
  python cli.py status --run-id RUN_XXX
  python cli.py result --run-id RUN_XXX
  python cli.py cancel --run-id RUN_XXX
  python cli.py list
"""

import argparse
import json
import os
import sys

# 同目录导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mobile_use_agent import (
    MobileUseAgentClient,
    format_steps,
    format_result,
)
from error_codes import (
    MobileUseError,
    format_error,
    CATEGORY_AUTH,
    CATEGORY_RESOURCE,
    CATEGORY_HITL,
)
from credential_store import (
    load_credentials,
    get_credentials_interactive,
    delete_credentials,
    mask_secret,
    has_credentials,
    CREDENTIALS_FILE,
)
from geo import ask_location_permission, acquire_gps


def print_json(data):
    """格式化输出 JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def show_api_error(e: MobileUseError):
    """展示 API 错误及按分类的差异化引导"""
    print(f"\n[API 错误]")
    print(format_error(e))
    # 按分类给特殊引导
    if e.category == CATEGORY_AUTH:
        if e.code == "ErrAssumeRoleFailed":
            print()
            print("[引导] 需要先为账号授权跨服务访问 (Mobile Use Agent 调用 IPAAS):")
            print("       控制台 → 访问控制 → 跨服务访问请求 → 授权 ServiceName=ipaas")
        else:
            print()
            print("[引导] 凭证无效或已过期, 请重新配置:")
            print("       python cli.py setup")
    elif e.category == CATEGORY_RESOURCE:
        print()
        print("[引导] 请在云手机控制台检查:")
        print("       - 业务 ID (ProductId) 是否正确且已开通 Mobile Use Agent")
        print("       - 实例 ID (PodId) 是否存在且处于运行状态")
    elif e.category == CATEGORY_HITL:
        print()
        print("[引导] 该任务需要人工介入 (HITL):")
        print("       - HITL_MORE_INFO      → 补充任务所需信息后重新发起")
        print("       - HITL_APPROVE        → 由管理员/用户完成审批")
        print("       - HITL_HUMAN_HELP     → 在云手机上完成手动操作后重试")


def get_client(force_setup: bool = False) -> MobileUseAgentClient:
    """获取已配置凭证的客户端

    优先使用命令行传入的 --ak/--sk;
    否则从本地加载; 本地也没有则引导首次配置。
    """
    ak, sk = get_credentials_interactive(force_setup=force_setup)
    return MobileUseAgentClient(ak=ak, sk=sk)


def get_product_pod():
    """交互式获取 ProductId/PodId (每次任务都要求输入)"""
    print("\n--- 云手机实例配置 ---")
    product_id = input("请输入 ProductId (云手机业务 ID): ").strip()
    pod_id = input("请输入 PodId (云手机实例 ID): ").strip()

    if not product_id or not pod_id:
        print("[错误] ProductId 和 PodId 不能为空!")
        return None, None

    return product_id, pod_id


def cmd_setup(args):
    """重新配置 AK/SK 凭证"""
    if has_credentials():
        saved = load_credentials()
        if saved:
            print(f"当前已保存凭证: AK = {mask_secret(saved[0])}")
            confirm = input("将覆盖已有凭证, 继续? [y/N]: ").strip().lower()
            if confirm != "y":
                print("已取消")
                return

    ak, sk = get_credentials_interactive(force_setup=True)


def cmd_whoami(args):
    """查看凭证状态"""
    saved = load_credentials()
    if saved:
        ak, sk = saved
        print(f"凭证文件: {CREDENTIALS_FILE}")
        print(f"AK:       {mask_secret(ak)}")
        print(f"SK:       {mask_secret(sk)}")
        print("\n如需重新配置, 运行: python cli.py setup")
    else:
        print("尚未配置凭证")
        print(f"首次运行任意命令时会自动引导配置, 或运行: python cli.py setup")


def cmd_logout(args):
    """删除本地凭证"""
    if not has_credentials():
        print("没有已保存的凭证")
        return

    saved = load_credentials()
    if saved:
        print(f"将删除凭证: AK = {mask_secret(saved[0])}")
    confirm = input("确认删除? [y/N]: ").strip().lower()
    if confirm != "y":
        print("已取消")
        return

    if delete_credentials():
        print(f"[成功] 已删除 {CREDENTIALS_FILE}")
    else:
        print("[失败] 删除失败")


def cmd_run_one_step(client, args):
    """一键运行代理任务 (ProductId/PodId/提示词每次输入)"""
    product_id = args.product_id
    pod_id = args.pod_id
    user_prompt = args.prompt

    # 缺哪个就交互式补哪个
    if not product_id or not pod_id:
        product_id, pod_id = get_product_pod()
        if not product_id:
            return

    if not user_prompt:
        print("\n--- 任务配置 ---")
        user_prompt = input("请输入用户提示词 (你想让 Agent 做什么): ").strip()

    if not user_prompt:
        print("[错误] UserPrompt 不能为空!")
        return

    run_name = args.run_name or f"mua-task-{int(__import__('time').time())}"

    # 高级参数
    max_step = args.max_step if args.max_step else 100
    timeout = args.timeout if args.timeout else 300
    system_prompt = args.system_prompt or None

    if not args.no_interactive:
        print(f"\n--- 高级参数 (回车使用默认值) ---")
        max_step_input = input(f"最大步数 [{max_step}]: ").strip()
        if max_step_input:
            max_step = int(max_step_input)
        timeout_input = input(f"超时时间(秒) [{timeout}]: ").strip()
        if timeout_input:
            timeout = int(timeout_input)
        system_prompt = (
            input("系统提示词 (可选, 回车跳过): ").strip() or None
        )

    # --- GPS 定位注入 (每次任务前询问) ---
    gps_info = None
    if args.gps:
        # 非交互模式下命令行显式授权
        gps_info = acquire_gps()
    elif not args.no_interactive:
        print("\n--- GPS 定位注入 ---")
        if ask_location_permission():
            gps_info = acquire_gps()
        else:
            print("[跳过] 已拒绝获取位置, 本次任务不注入 GpsInfo")

    result = client.run_and_wait(
        run_name=run_name,
        pod_id=pod_id,
        product_id=product_id,
        user_prompt=user_prompt,
        max_step=max_step,
        timeout=timeout,
        system_prompt=system_prompt,
        gps_info=gps_info,
    )

    print("\n" + "=" * 60)
    print("  [最终结果]")
    print("=" * 60)
    print(format_result(result))


def cmd_status(client, args):
    """查询任务当前步骤"""
    run_id = args.run_id
    if not run_id:
        run_id = input("请输入 RunId: ").strip()
    if not run_id:
        print("[错误] RunId 不能为空!")
        return

    resp = client.list_agent_run_current_step(run_id)
    print("\n" + "=" * 60)
    print(f"  [任务步骤] RunId: {run_id}")
    print("=" * 60)
    print(format_steps(resp))


def cmd_result(client, args):
    """获取任务运行结果"""
    run_id = args.run_id
    if not run_id:
        run_id = input("请输入 RunId: ").strip()
    if not run_id:
        print("[错误] RunId 不能为空!")
        return

    resp = client.get_agent_result(run_id)
    print("\n" + "=" * 60)
    print(f"  [任务结果] RunId: {run_id}")
    print("=" * 60)
    print(format_result(resp))


def cmd_cancel(client, args):
    """取消代理任务"""
    run_id = args.run_id
    if not run_id:
        run_id = input("请输入 RunId: ").strip()
    if not run_id:
        print("[错误] RunId 不能为空!")
        return

    confirm = input(f"确认取消任务 {run_id}? [y/N]: ").strip()
    if confirm.lower() != "y":
        print("已取消操作")
        return

    resp = client.cancel_task(run_id)
    print_json(resp)


def cmd_list(client, args):
    """查询代理任务列表"""
    resp = client.list_agent_run_task(
        run_id=args.run_id,
        run_name=args.run_name,
        page_size=args.page_size or 10,
        page_number=args.page_number or 1,
    )
    print_json(resp)


def cmd_config_create(client, args):
    """创建代理运行配置"""
    max_step = args.max_step or 55
    timeout = args.timeout or 300

    if not args.no_interactive:
        max_step_input = input(f"最大步数 [{max_step}]: ").strip()
        if max_step_input:
            max_step = int(max_step_input)
        timeout_input = input(f"超时时间(秒) [{timeout}]: ").strip()
        if timeout_input:
            timeout = int(timeout_input)

    config_id = client.create_agent_run_config(
        max_step=max_step,
        timeout=timeout,
        tos_bucket=args.tos_bucket or "",
        tos_endpoint=args.tos_endpoint or "",
        tos_region=args.tos_region or "",
        callback_url=args.callback_url or "",
    )
    print(f"\n[成功] ConfigId: {config_id}")


def cmd_config_list(client, args):
    """查询代理运行配置列表"""
    resp = client.list_agent_run_config(
        page_size=args.page_size or 10,
        page_number=args.page_number or 1,
    )
    print_json(resp)


def cmd_config_delete(client, args):
    """删除代理运行配置"""
    config_id = args.config_id
    if not config_id:
        config_id = input("请输入 ConfigId: ").strip()
    if not config_id:
        print("[错误] ConfigId 不能为空!")
        return

    resp = client.delete_agent_run_config(config_id)
    print_json(resp)


def interactive_menu(client):
    """交互式菜单 (凭证已就绪)"""

    while True:
        print("\n" + "=" * 50)
        print("  Mobile Use Agent - 交互式菜单")
        print("=" * 50)
        print("  1. 运行代理任务  (每次输入实例/提示词)")
        print("  2. 查询任务当前步骤")
        print("  3. 获取任务运行结果")
        print("  4. 取消代理任务")
        print("  5. 查询代理任务列表")
        print("  6. 创建代理运行配置")
        print("  7. 查询代理运行配置列表")
        print("  8. 删除代理运行配置")
        print("  9. 重新配置凭证 (AK/SK)")
        print("  0. 退出")
        print("=" * 50)

        choice = input("请选择操作: ").strip()

        if choice == "1":
            product_id, pod_id = get_product_pod()
            if not product_id:
                continue
            user_prompt = input("用户提示词: ").strip()
            if not user_prompt:
                print("[错误] 提示词不能为空!")
                continue

            run_name = input("运行名称 (回车自动生成): ").strip()
            max_step_input = input("最大步数 [100]: ").strip()
            max_step = int(max_step_input) if max_step_input else 100
            timeout_input = input("超时时间(秒) [300]: ").strip()
            timeout = int(timeout_input) if timeout_input else 300

            # GPS 定位注入 (每次询问)
            print("\n--- GPS 定位注入 ---")
            gps_info = None
            if ask_location_permission():
                gps_info = acquire_gps()
            else:
                print("[跳过] 已拒绝获取位置, 本次任务不注入 GpsInfo")

            result = client.run_and_wait(
                run_name=run_name or None,
                pod_id=pod_id,
                product_id=product_id,
                user_prompt=user_prompt,
                max_step=max_step,
                timeout=timeout,
                gps_info=gps_info,
            )
            print("\n[结果]")
            print(format_result(result))

        elif choice == "2":
            run_id = input("请输入 RunId: ").strip()
            if run_id:
                resp = client.list_agent_run_current_step(run_id)
                print("\n" + "=" * 60)
                print(f"  [任务步骤] RunId: {run_id}")
                print("=" * 60)
                print(format_steps(resp))

        elif choice == "3":
            run_id = input("请输入 RunId: ").strip()
            if run_id:
                resp = client.get_agent_result(run_id)
                print("\n" + "=" * 60)
                print(f"  [任务结果] RunId: {run_id}")
                print("=" * 60)
                print(format_result(resp))

        elif choice == "4":
            run_id = input("请输入 RunId: ").strip()
            if run_id:
                confirm = input(f"确认取消? [y/N]: ").strip()
                if confirm.lower() == "y":
                    resp = client.cancel_task(run_id)
                    print_json(resp)

        elif choice == "5":
            resp = client.list_agent_run_task()
            print_json(resp)

        elif choice == "6":
            max_step_input = input("最大步数 [55]: ").strip()
            max_step = int(max_step_input) if max_step_input else 55
            timeout_input = input("超时时间(秒) [300]: ").strip()
            timeout = int(timeout_input) if timeout_input else 300

            config_id = client.create_agent_run_config(
                max_step=max_step, timeout=timeout
            )
            print(f"\n[成功] ConfigId: {config_id}")

        elif choice == "7":
            resp = client.list_agent_run_config()
            print_json(resp)

        elif choice == "8":
            config_id = input("请输入 ConfigId: ").strip()
            if config_id:
                resp = client.delete_agent_run_config(config_id)
                print_json(resp)

        elif choice == "9":
            get_credentials_interactive(force_setup=True)
            client = get_client()

        elif choice == "0":
            print("再见!")
            break
        else:
            print("无效选择, 请重试")


def main():
    parser = argparse.ArgumentParser(
        description="Mobile Use Agent CLI - 火山引擎云手机 Agent OpenAPI 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 全局凭证参数 (可选, 覆盖本地保存的凭证)
    parser.add_argument(
        "--ak", default=os.environ.get("VOLC_ACCESSKEY", ""),
        help="Access Key ID (不传则使用本地保存的凭证)"
    )
    parser.add_argument(
        "--sk", default=os.environ.get("VOLC_SECRETKEY", ""),
        help="Secret Access Key (不传则使用本地保存的凭证)"
    )

    subparsers = parser.add_subparsers(dest="command", help="操作命令")

    # setup - 配置凭证
    subparsers.add_parser("setup", help="配置/重新配置 AK/SK 凭证")

    # whoami - 查看凭证状态
    subparsers.add_parser("whoami", help="查看当前凭证状态")

    # logout - 删除本地凭证
    subparsers.add_parser("logout", help="删除本地保存的凭证")

    # run - 运行代理任务 (每次输入 ProductId/PodId/提示词)
    p_run = subparsers.add_parser("run", help="运行代理任务 (RunAgentTaskOneStep)")
    p_run.add_argument("--product-id", default="", help="云手机业务 ID")
    p_run.add_argument("--pod-id", default="", help="云手机实例 ID")
    p_run.add_argument("--run-name", default="", help="运行名称")
    p_run.add_argument("--prompt", default="", help="用户提示词")
    p_run.add_argument("--max-step", type=int, default=0, help="最大步数 (默认 100)")
    p_run.add_argument("--timeout", type=int, default=0, help="超时时间秒 (默认 300)")
    p_run.add_argument("--system-prompt", default="", help="系统提示词")
    p_run.add_argument(
        "--gps", action="store_true",
        help="允许获取当前位置并注入 GpsInfo (非交互模式下自动获取, 不再询问)"
    )
    p_run.add_argument("--no-interactive", action="store_true", help="跳过交互式参数确认")

    # status - 查询当前步骤
    p_status = subparsers.add_parser("status", help="查询任务当前步骤")
    p_status.add_argument("--run-id", default="", help="运行 ID")

    # result - 获取结果
    p_result = subparsers.add_parser("result", help="获取任务运行结果")
    p_result.add_argument("--run-id", default="", help="运行 ID")

    # cancel - 取消任务
    p_cancel = subparsers.add_parser("cancel", help="取消代理任务")
    p_cancel.add_argument("--run-id", default="", help="运行 ID")

    # list - 列出任务
    p_list = subparsers.add_parser("list", help="查询代理任务列表")
    p_list.add_argument("--run-id", default="", help="运行 ID (筛选)")
    p_list.add_argument("--run-name", default="", help="运行名称 (筛选)")
    p_list.add_argument("--page-size", type=int, default=0, help="每页数量")
    p_list.add_argument("--page-number", type=int, default=0, help="页码")

    # config create
    p_cc = subparsers.add_parser("config-create", help="创建代理运行配置")
    p_cc.add_argument("--max-step", type=int, default=0, help="最大步数 (默认 55)")
    p_cc.add_argument("--timeout", type=int, default=0, help="超时时间秒 (默认 300)")
    p_cc.add_argument("--tos-bucket", default="", help="TOS 存储桶")
    p_cc.add_argument("--tos-endpoint", default="", help="TOS 端点")
    p_cc.add_argument("--tos-region", default="", help="TOS 区域")
    p_cc.add_argument("--callback-url", default="", help="回调 URL")
    p_cc.add_argument("--no-interactive", action="store_true", help="跳过交互式确认")

    # config list
    p_cl = subparsers.add_parser("config-list", help="查询代理运行配置列表")
    p_cl.add_argument("--page-size", type=int, default=0, help="每页数量")
    p_cl.add_argument("--page-number", type=int, default=0, help="页码")

    # config delete
    p_cd = subparsers.add_parser("config-delete", help="删除代理运行配置")
    p_cd.add_argument("--config-id", default="", help="配置 ID")

    args = parser.parse_args()

    # ---------- 凭证管理类命令 (无需 API 客户端) ----------
    if args.command == "setup":
        cmd_setup(args)
        return
    if args.command == "whoami":
        cmd_whoami(args)
        return
    if args.command == "logout":
        cmd_logout(args)
        return

    # ---------- 获取凭证 ----------
    ak = args.ak
    sk = args.sk

    if ak and sk:
        # 命令行/环境变量显式传入: 直接使用, 不读本地
        client = MobileUseAgentClient(ak=ak, sk=sk)
    else:
        # 本地加载 -> 首次引导配置并保存
        client = get_client()

    # ---------- 无命令 -> 交互式菜单 ----------
    if not args.command:
        interactive_menu(client)
        return

    # ---------- 分发命令 ----------
    handlers = {
        "run": cmd_run_one_step,
        "status": cmd_status,
        "result": cmd_result,
        "cancel": cmd_cancel,
        "list": cmd_list,
        "config-create": cmd_config_create,
        "config-list": cmd_config_list,
        "config-delete": cmd_config_delete,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return

    try:
        handler(client, args)
    except KeyboardInterrupt:
        print("\n[中断] 操作已取消")
    except SystemExit:
        raise
    except MobileUseError as e:
        # 带错误码的 API 错误: 展示中文描述 + 操作建议 + 分类引导
        show_api_error(e)
    except Exception as e:
        # 其他异常: 友好呈现, 凭证失效时给出重新配置提示
        msg = str(e)
        print(f"\n[错误] {type(e).__name__}: {msg[:500]}")

        if "InvalidAccessKey" in msg or "Unauthorized" in msg or "401" in msg:
            print("\n[提示] 凭证无效或已过期, 请重新配置:")
            print("       python cli.py setup")


if __name__ == "__main__":
    main()
