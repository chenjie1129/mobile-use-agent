---
name: mobile-use-agent
description: Run AI agent tasks on a Volcengine (火山引擎) cloud phone via the Mobile Use Agent OpenAPI. Use when the user asks to drive, automate, operate, or test an Android app on a cloud phone (e.g. open 小红书 and search, place an order, check nearby places on a map), or to check status, fetch result, cancel, or list a Mobile Use run. Requires one-time setup to store Volcengine AK/SK locally; ProductId, PodId and the user prompt are provided per run. Supports optional GPS injection (GpsInfo) with user consent.
license: MIT
agent_created: true
metadata:
  author: chenjie1129
  version: "1.0.0"
---

# Mobile Use Agent - 火山引擎云手机 Agent

通过火山引擎 Mobile Use Agent OpenAPI 在云手机上执行 AI Agent 任务（UI 自动化操作 Android App）。本 skill 提供 CLI 入口和完整工作流封装。

所有相对路径均以本 skill 的根目录（含 SKILL.md 的目录）为基准解析。

## 安全边界 (Safety Boundary)

- **发起/取消任务**会改变外部状态并可能产生云资源费用，仅在用户明确要求时执行。查询类操作（status/result/list/whoami）为只读，可随时执行。
- **绝不**要求用户在聊天中粘贴 AK/SK、不打印密钥、不把密钥放进命令行参数、不把密钥保存进本 skill 目录。让用户在自己可信的终端中运行交互式 `setup`（SK 输入不回显）。
- 本地配置检查只是客户端校验，不代表云手机任务真实成功。不要声称任务成功，除非有真实返回结果。

## 检查可用性

首次调用可能自动安装 Python 依赖（`pip install -r requirements.txt`）。

```sh
python3 scripts/cli.py whoami
```

- 若提示"未配置凭证"，请用户在自己的终端运行 `python3 scripts/cli.py setup` 完成一次性配置（AK/SK 保存到 `~/.mobile_use_agent/credentials.json`，权限 600）。
- 若依赖缺失，先执行 `pip install -r requirements.txt`。

## 执行用户请求的任务

默认走最便捷的 `RunAgentTaskOneStep`（免预创建配置），自动轮询步骤并实时增量打印，最后拉取最终结果：

```sh
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "打开小红书并搜索咖啡"
```

- **PID / POD 每次由用户提供**（或交互输入）；提示词为用户想让 Agent 执行的操作。
- 任务执行中步骤会增量打印（`-- Step N [OK]`），结束后展示状态/内容/截屏 URL/用量；失败时自动归因（打印中文失败原因、操作建议、错误码）。
- 轮询/取消/续跑/录屏/输出 schema 等高级用法见 [references/commands.md](references/commands.md)。

### GPS 定位注入（可选）

云手机无 GPS 硬件，可通过 `GpsInfo` 注入虚拟定位（地图类 App 显示指定位置）。每次发起任务前询问用户是否允许获取本机位置：

```sh
# 交互式：程序会询问"是否允许获取当前位置"（拒绝则不注入，功能不受影响）
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "打开地图查看附近美食"

# 非交互/已授权：--gps 显式允许并注入
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "打开地图" --gps --no-interactive
```

定位策略自动降级：macOS CoreLocation（米级）→ IP 定位（城市级 ±10km），坐标系 WGS-84。获取结果会告知用户（来源/坐标/精度）。详见 [references/gps.md](references/gps.md)。

## 只读查询

```sh
python3 scripts/cli.py status --run-id RUN_XXX   # 查询任务当前步骤
python3 scripts/cli.py result --run-id RUN_XXX   # 获取任务运行结果
python3 scripts/cli.py list                      # 查询任务列表
```

## 错误处理

所有 API 错误统一转为 `MobileUseError`（错误码 + 中文描述 + 操作建议 + 分类）。认证类错误提示用户重新 `setup`；资源类错误提示检查 ProductId/PodId；`ErrAssumeRoleFailed` 提示去控制台授权 `ServiceName=ipaas`。完整错误码表和双通道捕获说明见 [references/error_codes.md](references/error_codes.md)。

## 编程式调用

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from mobile_use_agent import MobileUseAgentClient
from credential_store import load_credentials

ak, sk = load_credentials()                       # 复用本地凭证
client = MobileUseAgentClient(ak=ak, sk=sk)
result = client.run_and_wait(
    run_name="my-task", pod_id="POD", product_id="PID",
    user_prompt="打开微信", gps_info=None,        # 每次动态传入
)
```

更多示例见 [scripts/examples.py](scripts/examples.py)。
