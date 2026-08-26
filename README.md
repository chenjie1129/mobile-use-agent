# Mobile Use Agent

在火山引擎**云手机**上执行 AI Agent 任务：让 AI 帮你操作 Android 手机里的 App——打开小红书搜索、下单、看地图、查桌面……支持一键全局命令 `mua`，配置一次，之后只需描述任务。

> 本包同时是**标准 WorkBuddy Skill**（`SKILL.md` 定义触发与工作流，WorkBuddy 可自动识别调用）、**独立 CLI 应用**，以及可嵌入你自有 Agent 的 **Python 工具库**（见下文「集成到你的 AI Agent」）。

## 快速开始（三步）

```bash
# 1. 安装（提供全局命令 mua）
./install.sh

# 2. 配置凭证（仅首次，SK 输入不回显；可顺便保存"默认手机"）
mua setup

# 3. 运行任务（问答式向导）
mua run
```

第 3 步的交互长这样：

```
请描述任务: 打开小红书搜索咖啡
[手机] 使用默认云手机: ProductId=prod-1f3a****d5a6  PodId=pod-87****4321
-- Step 1 [OK] --
   [action] finished
   [content] 已成功打开小红书并搜索咖啡, 任务完成。
[任务结束] 状态: 成功
```

**之后每次只需 `mua run` 输入任务描述**——默认手机已记住，回车即用。

> ⚠️ 前提：你需要先完成下方「开通与准备」——没有开通服务和云手机资源，`mua run` 无法执行。

## 开通与准备（按官方指引）

以下流程依据火山引擎官方文档 [控制台常见操作指引](https://docs.volcengine.com/docs/6394/2280699?lang=zh) 整理，按顺序完成即可。已开通过的用户可跳过本节。

### 1. 账号与角色授权（一次性）

让云手机服务有权访问对象存储等其他服务，需要完成**两项角色授权**：

- **授权 ServiceRoleForIPaaS**：点击 [ServiceRoleForIPaaS 授权链接](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas)，单击"立即授权"。
- **创建 PaasServiceRole 角色**（约 2 分钟）：
  1. 打开 [角色管理](https://console.volcengine.com/iam/identitymanage/role/)，单击"新建角色"；
  2. 信任身份选择"服务"，服务选择"云手机"，单击"下一步"；
  3. 角色名填写 `PaasServiceRole`，单击"下一步"；
  4. 勾选全部策略，作用范围选"全局"，单击"提交"。

### 2. 开通 Mobile Use Agent 服务（一次性）

1. 登录 [云手机控制台](https://console.volcengine.com/ACEP/Business/6)；
2. 单击页面"立即开通"；
3. 弹窗中确认 Mobile Use Agent Token 计费项，阅读并同意《产品服务条款》和《服务等级协议》，单击"立即开通"。

### 3. 创建 MUA 业务 → 获得 **ProductId**

MUA 业务是使用本服务的基础单元，**ProductId 即业务 ID**：

1. 登录 [MUA 控制台](https://console.volcengine.com/ACEP/mua/)；
2. 若账号下尚无业务，系统自动弹出新建业务框；若已有业务，在左侧目录树顶部展开业务列表，单击"+ 新建业务"；
3. 填写业务名称（可添加子账号），单击"确定"；
4. 创建后在**业务管理页**查看业务 ID，即为 `ProductId`。

### 4. 订购云手机资源 → 获得 **PodId**

云手机资源为业务提供真实可操作的云端手机实例，**PodId 即云手机实例 ID**：

1. 在 [MUA 控制台](https://console.volcengine.com/ACEP/mua/) 左侧目录树单击"+ 新任务"；
2. 对话框左下角单击"+ 订购云手机"，跳转购买页配置（地域、计费方式、云机规格 8vCPU｜24GB｜256GB、购买数量）；
3. 确认订单并完成购买；
4. ⚠️ 首次订购需约 **2～3 分钟**开通，开通后到「**云手机资源**」页面查看实例 ID，即为 `PodId`；
5. ⚠️ 实例需保持"**运行中**"状态才可正常使用。

### 5. 获取 AK / SK

控制台 → 右上角头像 → **访问密钥**（Access Key），创建后得到 AK/SK 一对。

> 📎 相关官方文档：[创建 MUA 业务](https://docs.volcengine.com/docs/6394/2298713)、[创建云手机资源](https://docs.volcengine.com/docs/6394/2604742)、[配置技能](https://docs.volcengine.com/docs/6394/2298758)、[配置应用操作指南](https://docs.volcengine.com/docs/6394/2298757)

---

拿到 `ProductId` / `PodId` / `AK` / `SK` 后，运行 `mua setup` 一次性保存（默认手机可选保存），之后即可 `mua run`。

## 常用操作速查

```bash
mua setup          # 配置/更换 AK/SK、默认手机
mua whoami         # 查看凭证与默认手机状态
mua device         # 查看默认手机（--clear 清除）
mua run            # 运行任务（问答式向导）
mua status --run-id RUN_XXX    # 查询任务进度
mua result --run-id RUN_XXX    # 获取任务结果
mua cancel --run-id RUN_XXX    # 取消任务
mua list           # 任务列表
mua                # 交互式菜单（不输入命令时）
```

完整命令与参数见 [references/commands.md](references/commands.md)。

## 特性

- **零重复输入**：AK/SK 与默认手机持久化本地（权限 600），运行时回车沿用
- **任务过程实时打印**：步骤增量输出，失败自动归因（原因/建议/错误码）
- **GPS 定位注入**（可选）：仅任务涉及位置时询问；CoreLocation 米级 → IP 城市级自动降级
- **错误码适配**：双通道捕获（HTTP 200 业务错误 + ApiException），统一中文提示与引导

## 集成到你的 AI Agent

如果你**已经有一个自己的 Agent**（基于 LangChain / LlamaIndex / 自研 function-calling / 任何 LLM 应用），想给它加上"操作真实手机"的能力，本仓库的 `scripts/` 就是可直接 import 的 Python 工具库。

### 安装与引入

```bash
git clone https://github.com/chenjie1129/mobile-use-agent.git
pip install -r mobile-use-agent/requirements.txt
```

```python
import sys
sys.path.insert(0, "/path/to/mobile-use-agent/scripts")   # 指向 scripts/ 目录

from mobile_use_agent import MobileUseAgentClient
from credential_store import load_profile    # {ak, sk, product_id, pod_id}
```

凭证复用 `mua setup` 已保存的本地配置（权限 600），**代码中不出现任何密钥**。

### 方式一：注册为工具（function calling，推荐）

把你的 LLM 当成"指挥官"，云手机操作作为一把工具交给它：

```python
profile = load_profile()
client = MobileUseAgentClient(ak=profile["ak"], sk=profile["sk"])

# 1) 工具 schema：交给你的 LLM（OpenAI / 通义 / 自研均可）
MUA_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "operate_cloud_phone",
        "description": "在火山引擎云手机上执行真实手机操作（打开App、搜索、下单、看地图等），返回任务结果",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "自然语言描述想执行的操作，如「打开小红书搜索咖啡」"},
                "product_id": {"type": "string", "description": "MUA 业务 ID，留空使用默认手机"},
                "pod_id": {"type": "string", "description": "云手机实例 ID，留空使用默认手机"},
            },
            "required": ["prompt"],
        },
    },
}

# 2) 工具实现：LLM 决定调用时，你的代码执行到这里
def operate_cloud_phone(prompt: str, product_id: str = "", pod_id: str = "") -> dict:
    product_id = product_id or profile["product_id"]   # 默认手机回退
    pod_id = pod_id or profile["pod_id"]
    if not product_id or not pod_id:
        raise ValueError("缺少 ProductId/PodId：先运行 `mua setup` 保存默认手机，或调用时传入")

    return client.run_and_wait(
        run_name="agent-tool-task",
        product_id=product_id,
        pod_id=pod_id,
        user_prompt=prompt,
        gps_info=None,   # 可选：位置相关任务可先征求用户同意，再调 geo.acquire_gps() 注入
    )
```

### 方式二：直接调用客户端 API（异步 / 事件驱动）

任务执行是"启动 → 轮询 → 取结果"三步，适合不想阻塞 Agent 主循环的场景：

```python
# 启动任务 → 立刻拿到 RunId 返回（任务在云手机后台继续执行）
resp = client.run_agent_task_one_step(
    run_name="async-task",
    product_id=profile["product_id"],
    pod_id=profile["pod_id"],
    user_prompt="打开微信",
)
run_id = resp["RunId"]

# 稍后按需查询（可挂在你的定时任务 / 回调 / 轮询循环里）
steps  = client.list_agent_run_current_step(run_id)   # 当前执行到哪一步
result = client.get_agent_result(run_id)              # 最终结果（含截屏/输出）
client.cancel_task(run_id)                            # 需要时取消
```

### 核心接口一览

| 客户端方法 | 对应 OpenAPI | 用途 |
|---|---|---|
| `run_agent_task_one_step` | RunAgentTaskOneStep | 启动任务（免预配置），返回 `RunId` |
| `list_agent_run_current_step` | ListAgentRunCurrentStep | 查询任务当前执行步骤 |
| `get_agent_result` | GetAgentResult | 获取最终结果 |
| `cancel_task` | CancelTask | 取消任务 |
| `list_agent_run_task` | ListAgentRunTask | 查询任务列表 |
| `run_and_wait` | 组合封装 | 启动 + 轮询 + 取结果（阻塞式） |

GPS 注入、TOS 截图存储、录屏、第三方 MCP 工具、输出 Schema 等更多参数见 [scripts/examples.py](scripts/examples.py)（5 个可直接运行场景）与 [references/api_reference.md](references/api_reference.md)。

## 高级用法

### 命令行直接传参（跳过向导，适合脚本）

```bash
mua run --product-id PID --pod-id POD --prompt "打开微信" --gps --no-interactive
```

### 目录结构

```
mobile-use-agent/
├── SKILL.md               # Skill 入口: 触发场景 + 安全边界 + 工作流
├── bin/mua                # 全局命令入口
├── install.sh             # 一键安装 mua
├── scripts/               # 可执行代码 + 可 import 的工具库
│   ├── cli.py             # 交互式 CLI + 命令行模式 (主入口)
│   ├── mobile_use_agent.py  # 核心客户端, 封装 10 个 OpenAPI
│   ├── error_codes.py     # 错误码定义与解析
│   ├── credential_store.py  # 凭证 + 默认手机持久化
│   └── geo.py             # 定位获取 (CoreLocation + IP 降级)
├── references/            # 按需加载的参考文档
│   ├── commands.md        # 命令参考
│   ├── error_codes.md     # 错误码参考
│   ├── gps.md             # GPS 注入参考
│   └── api_reference.md   # OpenAPI 参考
└── requirements.txt       # Python 依赖
```

## 常见问题

**Q: 任务报 `ErrAssumeRoleFailed`？**
A: 未完成跨服务授权。按上文「开通与准备」第 1 步授权 [ServiceRoleForIPaaS](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas) 并创建 `PaasServiceRole` 角色后重试。

**Q: 找不到 ProductId / PodId？**
A: `ProductId` 是 **MUA 业务 ID**（[MUA 控制台](https://console.volcengine.com/ACEP/mua/) → 业务列表）；`PodId` 是**云手机实例 ID**（MUA 控制台 → 云手机资源）。找到后 `mua setup` 保存为默认手机，之后不用再找。

**Q: 报 `InvalidAccessKey`？**
A: 凭证无效或过期，运行 `mua setup` 重新配置。

**Q: 云手机实例"未运行"？**
A: 实例需保持"运行中"才可执行任务，在 MUA 控制台 → 云手机资源 启动后重试。

完整错误码表与处理见 [references/error_codes.md](references/error_codes.md)。

## 许可证

MIT
