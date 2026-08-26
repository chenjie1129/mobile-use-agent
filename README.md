# Mobile Use Agent - 火山引擎云手机 Agent 应用

调用火山引擎 **Mobile Use Agent OpenAPI** 的 Agent 应用。

## 凭证策略

| 参数 | 配置时机 | 说明 |
|---|---|---|
| **AK / SK** | **首次运行时配置一次** | 保存到 `~/.mobile_use_agent/credentials.json`（权限 600），后续自动加载 |
| **ProductId** | **每次发起任务时输入** | 云手机业务 ID |
| **PodId** | **每次发起任务时输入** | 云手机实例 ID |
| **用户提示词** | **每次发起任务时输入** | 想让 Agent 执行的操作 |
| **GPS 定位授权** | **每次发起任务时询问** | 允许后获取当前位置注入 GpsInfo，拒绝则不注入 |

首次运行任意命令时会自动引导配置 AK/SK；凭证失效时可运行 `setup` 重新配置。

## 文件结构

```
mobile-use-agent/
├── mobile_use_agent.py   # 核心客户端类 (MobileUseAgentClient), 封装 10 个 API
├── error_codes.py        # 错误码定义与解析 (公共 12 + 业务 32 + 认证 5)
├── credential_store.py   # AK/SK 凭证持久化 (~/.mobile_use_agent/)
├── geo.py                # 本地地理位置获取 (CoreLocation + IP 降级)
├── cli.py                # 交互式 CLI + 命令行模式
├── run.py                # 快速运行脚本 (最简模式)
├── examples.py           # 编程式调用示例 (5 个场景)
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量配置模板 (可选)
└── README.md             # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 首次配置凭证（只需一次）

```bash
python cli.py setup
```

按提示输入 AK/SK，保存到本地。也可以直接运行任意命令，首次会自动引导配置。

获取方式：火山引擎控制台 → 右上角头像 → 访问密钥

### 3. 运行任务（每次输入实例和提示词）

```bash
python cli.py run
```

流程：
```
[凭证] 已加载本地配置: AKLT********abcd   ← 自动加载，无需输入
--- 云手机实例配置 ---
请输入 ProductId (云手机业务 ID): xxx       ← 每次输入
请输入 PodId (云手机实例 ID): xxx           ← 每次输入
--- 任务配置 ---
请输入用户提示词: 打开设置查看系统版本       ← 每次输入
最大步数 [100]: 
超时时间(秒) [300]: 
--- GPS 定位注入 ---
是否允许获取当前位置并注入云手机 GPS? [y/N]: y
[定位] 已获取: 中国 上海市 上海, 北纬 31.222200, 东经 121.458100 (来源: IP 定位, 城市级)
[定位] GpsInfo 注入值: "121.458100,31.222200,0,0.0,0,10000"
```

## GPS 定位注入

云手机本身没有 GPS 硬件，`GpsInfo` 参数用于在任务启动前向云手机注入虚拟定位，让地图类 App 显示指定位置。

**每次发起任务前都会询问是否允许获取位置**，拒绝则本次任务不注入；允许则获取后告知结果（来源 / 坐标 / 精度），再传入 API。

### 获取策略（自动降级）

| 优先级 | 方式 | 精度 | 依赖 |
|---|---|---|---|
| 1 | macOS CoreLocation 系统定位 | 米级（含海拔/速度/方位角） | `pyobjc-framework-CoreLocation` + 终端定位权限 |
| 2 | IP 定位（ip-api.com → ipinfo.io → ipapi.co） | 城市级（±10km） | 无 |

**坐标系**：全部使用 WGS-84（火山引擎要求），刻意避开国内地图服务的 GCJ-02/BD-09 偏移坐标系。

**GpsInfo 格式**：`"经度,纬度,海拔,速度,方位角,定位精度"`
```
示例: "116.397128,39.916527,50,0,0,10"
     经度 116.397128, 纬度 39.916527, 海拔 50m, 速度 0m/s, 方位角 0°, 精度 ±10m
```

### 终端定位权限（macOS 精确定位）

首次运行会触发系统授权弹窗，也可手动开启：
`系统设置 → 隐私与安全性 → 定位服务 → 终端（或你的终端 App）`

未授权时自动降级为 IP 城市级定位，功能不受影响。

### 非交互模式

```bash
# --gps 显式授权, 直接获取并注入 (跳过询问)
python cli.py run --product-id PID --pod-id POD --prompt "打开地图" --gps --no-interactive
```

### 单独测试定位

```bash
python geo.py    # 输出获取结果和 GpsInfo 字符串
```

### 4. 交互式菜单

```bash
python cli.py
```

提供任务运行、状态查询、结果获取、任务取消、配置管理等全部功能的菜单式操作。

### 5. 任务过程实时打印

运行任务时（`cli.py run` / `run.py` / 交互式菜单选项 1），Agent 在云手机上的执行步骤会**实时增量打印**，每步只出现一次，不重复刷屏：

```
  -- Step 1 [OK] 13:17:12 --
     [action] finished
     [content] 已成功下载、安装并打开小红书,当前进入小红书登录页面,任务完成。
     [result] 上一轮任务已经完成,结果是:已成功下载、安装并打开小红书。
  -- Step 2 [OK] 13:17:20 --
     [action] click
     [content] 点击'搜索'按钮
     [result] 点击成功

  [任务结束] 状态: 成功
```

- `[OK]` = 该步骤成功（StepResult.IsSuccess=true），`[FAIL]` = 失败
- 任务结束后自动拉取最终结果，展示状态、内容、截屏 TOS URL、用量
- `status` / `result` 命令同样以可读格式输出，而非原始 JSON

## 命令一览

```bash
# 凭证管理
python cli.py setup              # 配置/重新配置 AK/SK
python cli.py whoami             # 查看当前凭证状态 (脱敏展示)
python cli.py logout             # 删除本地保存的凭证

# 任务操作 (自动加载本地凭证)
python cli.py run                # 运行任务 (交互式输入 ProductId/PodId/提示词)
python cli.py run --product-id PID --pod-id POD --prompt "打开微信"  # 直接传参
python cli.py status --run-id RUN_XXX    # 查询任务当前步骤
python cli.py result --run-id RUN_XXX    # 获取任务运行结果
python cli.py cancel --run-id RUN_XXX    # 取消任务
python cli.py list                       # 查询任务列表

# 代理运行配置管理
python cli.py config-create      # 创建代理运行配置
python cli.py config-list        # 查询配置列表
python cli.py config-delete      # 删除配置

# 凭证优先级
# 命令行 --ak/--sk > 环境变量 VOLC_ACCESSKEY/VOLC_SECRETKEY > 本地凭证文件
```

## 错误码适配

数据来源: [火山引擎错误码文档](https://docs.volcengine.com/docs/6394/1956026)

所有 API 错误统一转换为 `MobileUseError` 异常（`error_codes.py`），携带中文描述、操作建议和错误分类，CLI 按分类给出差异化引导。

### 错误码表（摘要）

| 分类 | 典型错误码 | 含义 | CLI 引导 |
|---|---|---|---|
| 认证/授权 | `401 InvalidAccessKey` | AK/SK 无效 | 提示运行 `setup` 重配凭证 |
| 认证/授权 | `401100 ErrAssumeRoleFailed` | 跨服务未授权 | 提示去控制台授权 `ServiceName=ipaas` |
| 资源 | `400205 ErrCloudPhoneProductUnavailable` | ProductId 不存在/无权限 | 提示检查 ProductId |
| 资源 | `400206 ErrCloudPhonePodUnavailable` | PodId 不存在/不可用 | 提示检查 ProductId/PodId/实例状态 |
| 参数 | `400207 ErrCloudPhoneGPSInjectFailed` | GPS 注入失败 | 提示检查 GPS 参数 |
| 任务状态 | `400201 ErrTaskStillExecuting` | 任务仍在执行 | 轮询时自动继续等待 |
| 任务状态 | `4000001 AGENT_MAX_STEP_REACHED` | 步数超限 | 建议拆分任务 |
| 任务状态 | `4000003 AGENT_TIMEOUT` | 执行超时 | 建议检查卡顿 |
| 任务状态 | `4000004 AGENT_STUCK_LOOP` | 陷入死循环 | 建议终止任务调整提示词 |
| 人工介入 HITL | `5000001/5000002/5000003` | 需补充信息/审批/协助 | 提示人工介入流程 |
| 模型 | `6000001 MODEL_CALL_FAILED` | 模型调用失败 | 自动重试, 多次失败查额度 |
| 工具/环境 | `3000001 ENV_APP_NOT_INSTALLED` | App 未安装 | 提示安装 App 或改镜像 |
| 安全 | `9000001 SECURITY_BLOCKED` | 高风险操作被拦截 | 提示调整任务目标 |

完整表见 `error_codes.py`（公共 12 个 + 业务 32 个 + 平台认证 5 个）。

### 双通道错误捕获

SDK 只在 HTTP 非 2xx 时抛 `ApiException`；**HTTP 200 的业务错误**（如 Pod 不存在）会静默藏在响应体 `ResponseMetadata.Error` 里。客户端两层都做了适配：

```python
try:
    resp = client.run_agent_task_one_step(...)
except MobileUseError as e:
    print(e.desc)    # 中文描述
    print(e.advice)  # 操作建议
    print(e.category)  # 分类: auth/resource/task/hitl/...
```

### 任务失败自动归因

`run_and_wait` 轮询到 `GetAgentResult.IsSuccess=0` 时，自动扫描响应中的业务错误码并打印失败原因：

```
  [任务结束] 状态: 失败/未成功 (IsSuccess=0)
  [失败原因] 任务规划陷入死循环
  [操作建议] 终止任务并分析可观测链路, 调整提示词或任务目标
  [错误码]   4000004 AGENT_STUCK_LOOP
```

### 编程式调用

```python
from mobile_use_agent import MobileUseAgentClient
from error_codes import MobileUseError

client = MobileUseAgentClient(ak="YOUR_AK", sk="YOUR_SK")
try:
    result = client.run_agent_task_one_step(
        run_name="t", pod_id="POD", product_id="PID", user_prompt="打开微信"
    )
except MobileUseError as e:
    print(f"错误 {e.code_n} {e.code}: {e.desc}")
    print(f"建议: {e.advice}")
```

## 编程式调用

```python
from mobile_use_agent import MobileUseAgentClient
from credential_store import load_credentials

# 方式 1: 从本地凭证文件加载 (首次用 setup 配置)
ak, sk = load_credentials()
client = MobileUseAgentClient(ak=ak, sk=sk)

# 方式 2: 直接指定
client = MobileUseAgentClient(ak="YOUR_AK", sk="YOUR_SK")

# 每次任务动态传入 ProductId/PodId/提示词
result = client.run_and_wait(
    run_name="my-task",
    pod_id="YOUR_POD_ID",        # 每次传入
    product_id="YOUR_PRODUCT_ID", # 每次传入
    user_prompt="打开微信",       # 每次传入
    max_step=100,
    timeout=300,
)
print(result)

# 注入本地位置 (获取 + 告知结果 + 传入)
from geo import acquire_gps
gps_info = acquire_gps()          # 例: "121.458100,31.222200,0,0.0,0,10000"
result = client.run_and_wait(
    run_name="my-gps-task",
    pod_id="YOUR_POD_ID",
    product_id="YOUR_PRODUCT_ID",
    user_prompt="打开地图查看附近美食",
    gps_info=gps_info,            # 拒绝授权时不传即可
)
```

## API 接口列表

| 接口 | Action | 方法 | 说明 |
|---|---|---|---|
| `create_agent_run_config` | CreateAgentRunConfig | POST | 创建代理运行配置 |
| `update_agent_run_config` | UpdateAgentRunConfig | POST | 更新代理运行配置 |
| `delete_agent_run_config` | DeleteAgentRunConfig | POST | 删除代理运行配置 |
| `list_agent_run_config` | ListAgentRunConfig | GET | 查询代理运行配置列表 |
| `run_agent_task` | RunAgentTask | POST | 运行代理任务 (需 ConfigId) |
| `run_agent_task_one_step` | RunAgentTaskOneStep | POST | 一键运行代理任务 (无需配置) |
| `cancel_task` | CancelTask | POST | 取消代理任务 |
| `list_agent_run_current_step` | ListAgentRunCurrentStep | GET | 查询任务当前步骤 |
| `list_agent_run_task` | ListAgentRunTask | GET | 查询代理任务列表 |
| `get_agent_result` | GetAgentResult | GET | 获取任务运行结果 |

## 凭证安全

- 凭证文件保存在 `~/.mobile_use_agent/credentials.json`
- 文件权限 `600`（仅所有者可读写），目录权限 `700`
- CLI 展示时始终脱敏（如 `AKLT********abcd`）
- 输入 SK 时终端不回显（getpass）
- 凭证优先级：命令行参数 > 环境变量 > 本地文件

## RunAgentTaskOneStep 核心参数

| 参数 | 类型 | 必选 | 默认值 | 说明 |
|---|---|---|---|---|
| `RunName` | String | 是 | — | 运行名称 (1~127 字节) |
| `PodId` | String | 是 | — | 云手机实例 ID (每次传入) |
| `ProductId` | String | 是 | — | 云手机业务 ID (每次传入) |
| `UserPrompt` | String | 是 | — | 用户提示词 (每次传入, 最多 10000 字节) |
| `ThreadId` | String | 否 | 自动生成 | 线程 ID |
| `UseBase64Screenshot` | Boolean | 否 | false | Base64 编码传输截屏 |
| `MaxStep` | Integer | 否 | 100 | 最大步数 (1~500 或 -1) |
| `Timeout` | Integer | 否 | 120 | 超时秒数 (1~86400 或 -1) |
| `RetryLimit` | Integer | 否 | 3 | 失败重试次数 (0~10) |
| `SystemPrompt` | String | 否 | — | 系统提示词 (最多 20000 字符) |
| `TosBucket` | String | 否 | — | TOS 存储桶名称 |
| `TosEndpoint` | String | 否 | — | TOS 端点地址 |
| `TosRegion` | String | 否 | — | TOS 区域 |
| `IsScreenRecord` | Boolean | 否 | false | 是否开启录屏 |
| `McpJson` | String | 否 | — | 第三方 MCP 工具配置 (JSON) |
| `MaxOutputTokens` | Integer | 否 | 0 | 单次最大输出 Token 数 |
| `GpsInfo` | String | 否 | — | GPS 注入信息 |
| `OutputSchema` | String | 否 | — | 输出格式 (JSON 字符串) |
| `CallbackInfo` | dict | 否 | — | 回调配置 |

## 前置条件

1. **火山引擎账号** — 完成注册和实名认证
2. **获取 AK/SK** — 在火山引擎控制台获取 Access Key ID 和 Secret Access Key
3. **跨服务授权** — 访问 [跨服务访问请求](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas) 为账号授权
4. **云手机实例** — 在云手机控制台创建业务 (获取 ProductId) 和实例 (获取 PodId)
5. **(可选) 对象存储 TOS** — 如需存储截图/录屏，需创建 TOS 存储桶并配置

## 注意事项

- **QPS 限制**: RunAgentTaskOneStep 整体 QPS 50 次/秒，单用户 10 次/秒
- **MaxStep=-1 + Timeout=-1**: 任务会 7×24 持续运行，需手动 CancelTask 终止
- **录屏文件**: 有效期 24 小时，需配置 TOS 存储
- **默认 TOS**: 不传 TOS 参数时使用默认存储，任务完成后立即删除截图
- **凭证失效**: 运行时报 401/InvalidAccessKey 时，执行 `python cli.py setup` 重新配置
