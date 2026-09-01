---
name: mobile-use-agent
description: Run AI agent tasks and manage Volcengine (火山引擎) cloud phones through Mobile Use Agent and ACEP OpenAPI. Use for Android app automation, device discovery, instance lifecycle, app management, screenshots, diagnostics, networking, resources, task status, results, and recovery. ProductId and PodId are auto-discovered when unambiguous; missing resources return structured next actions. Credentials are read from environment variables only. Supports optional GPS injection with user consent and P0/P1/P2 confirmation gates for control-plane actions.
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

- **发起/取消任务**会改变外部状态并可能产生云资源费用，仅在用户明确要求时执行。查询类操作（status/result/list/whoami/resolve-device）为只读，可随时执行。
- **绝不**要求用户在聊天中粘贴 AK/SK、不打印密钥、不把密钥放进命令行参数或本地配置。凭证必须由凭证代理注入 `VOLC_ACCESSKEY`/`VOLC_SECRETKEY`。
- 云手机控制面按 P0/P1/P2 分级。P1/P2 必须传入与 Action 完全一致的 `--confirm-action`；未知 Action 默认按 P2 处理。
- 本地配置检查只是客户端校验，不代表云手机任务真实成功。不要声称任务成功，除非有真实返回结果。

## 检查可用性

首次调用可能需要 Python 依赖；推荐先让用户运行 `./install.sh`（自动创建独立 venv 并装好依赖，不污染系统 Python）。入口优先用全局命令 `mua`（已安装时），否则 `python3 scripts/cli.py`：

```sh
mua whoami                       # 或: python3 scripts/cli.py whoami
```

- 若提示"未配置凭证"，引导用户通过凭证代理设置 `VOLC_ACCESSKEY`/`VOLC_SECRETKEY`，再运行 `mua setup` 检查并可保存非敏感默认设备。
- 若用户表示**尚未开通 Mobile Use Agent 服务 / 没有云手机资源**（或问"ProductId/PodId 在哪找"），引导其查看 README「二、开始之前：一次性准备」——按官方四步指引依次完成：给云手机开权限（ServiceRoleForIPaaS + PaasServiceRole）→ 开通服务 → 创建业务（得 ProductId）→ 订购云手机资源（得 PodId）→ 创建密钥（得 AK/SK）。已开通过的用户无需此步骤。
- 若任务目标是**云手机未预装的应用**（默认镜像只预装少量 App），先引导用户在 [MUA 控制台「发布 App」](https://www.volcengine.com/docs/6394/1223958?lang=zh) 安装到云手机，再执行任务。
- 若任务执行中遇到**人脸识别验证**（如登录银行/支付类 App），引导用户用手机扫码完成验证（官方流程见 README「五、常见问题」）：云手机画面弹出二维码（或点"H5 扫码链接"）→ 手机扫码 → 手机端完成登录与人脸扫描 → 回控制台点"重新连接"。扫码期间云手机画面提示"连接异常"是正常现象。
- 若依赖缺失，优先让用户运行 `./install.sh`（建独立环境），避免往系统 Python 装包。

## 执行用户请求的任务

默认走最便捷的 `RunAgentTaskOneStep`（免预创建配置），自动轮询步骤并实时增量打印，最后拉取最终结果：

```sh
mua run --product-id PID --pod-id POD --prompt "打开企业微信，回复最新客户消息"
```

- **用户提示词每次提供**；**ProductId/PodId 优先用 setup 时保存的默认手机**（命令行参数可覆盖）。
- 缺少 ID 时先执行自动发现：唯一业务/运行中实例自动选择；多个候选返回选择列表；没有业务返回控制台创建入口；没有实例返回资源、规格、机房和 `CreatePodOneStep` 确认步骤。
- Agent/CI 必须使用 `--agent-json`，stdout 将输出 JSONL
  `started/progress/result/error` 事件。需要人工决策时命令输出结构化 JSON，
  不允许猜测 ProductId、PodId、DC 或规格。
- 任务执行中步骤会增量打印（`-- Step N [OK]`），结束后展示状态/内容/截屏 URL/用量；失败时自动归因（打印中文失败原因、操作建议、错误码）。
- 轮询/取消/续跑/录屏/输出 schema 等高级用法见 [references/commands.md](references/commands.md)。

### 缺少设备时

```sh
mua resolve-device --agent-json
```

根据 `status` 继续：

- `ready`：使用返回的 ProductId/PodId 发起任务。
- `product_selection_required` / `pod_selection_required`：请用户从候选项选择。
- `product_required`：请用户到控制台完成服务协议确认和业务创建。
- `pod_creation_required`：展示返回的资源、规格和机房；获得用户确认后使用
  `--create-pod ... --confirm-action CreatePodOneStep`。
- `power_on_required`：获得用户确认后使用
  `--auto-power-on --confirm-action PowerOnPod`。

资源订购、删除、重置、迁移、文件操作、ADB 和任意命令属于 P2，不得从
普通 `mua run` 自动触发。
完整状态协议与风险分级见
[references/control_plane.md](references/control_plane.md)。

### GPS 定位注入（可选）

云手机无 GPS 硬件，可通过 `GpsInfo` 注入虚拟定位（地图类 App 显示指定位置）。**仅当任务涉及位置时**（提示词含 附近/地图/导航/外卖/打车 等词）程序会自动询问用户是否允许获取本机位置；无关任务不打扰：

```sh
# 交互式：位置相关任务会询问"是否允许获取当前位置"（拒绝则不注入，功能不受影响）
mua run --product-id PID --pod-id POD --prompt "打开地图查看附近美食"

# 非交互/已授权：--gps 显式允许并注入
mua run --product-id PID --pod-id POD --prompt "打开地图" --gps --no-interactive
```

定位获取为**多来源统一接口 + 自动降级链**（按精度从高到低）：文本/分享链接坐标解析 → 图片 EXIF → macOS CoreLocation（米级，需授权）→ IP 定位（城市级）→ 地名地理编码 → 手动输入兜底。仅 `system` 来源需要系统授权，拒绝授权时仍可走解析/手动输入。坐标系统一 WGS-84。获取结果会告知用户（来源/坐标/精度）。详见 [references/gps.md](references/gps.md)。

## 只读查询

```sh
mua status --run-id RUN_XXX   # 查询任务当前步骤
mua result --run-id RUN_XXX   # 获取任务运行结果
mua list                      # 查询任务列表
mua whoami / mua device       # 凭证与默认手机状态
mua resolve-device --agent-json
mua phone-action ListPod --params-json '{"ProductId":"PID"}' --query
```

## 错误处理

所有 API 错误统一转为 `MobileUseError`（错误码 + 中文描述 + 操作建议 + 分类）。认证类错误提示用户重新 `setup`；资源类错误提示检查 ProductId/PodId；`ErrAssumeRoleFailed` 提示完成跨服务授权——[授权 ServiceRoleForIPaaS](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas) 并创建 `PaasServiceRole` 角色（详见 README「二、开始之前」第 1 步）。完整错误码表和双通道捕获说明见 [references/error_codes.md](references/error_codes.md)。

## 编程式调用

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from mobile_use_agent import MobileUseAgentClient
from credential_store import load_credentials

ak, sk = load_credentials()                       # 从环境变量读取
client = MobileUseAgentClient(ak=ak, sk=sk)
result = client.run_and_wait(
    run_name="my-task", pod_id="POD", product_id="PID",
    user_prompt="打开企业微信查看未读消息", gps_info=None,   # 每次动态传入
)
```

更多示例见 [scripts/examples.py](scripts/examples.py)。
