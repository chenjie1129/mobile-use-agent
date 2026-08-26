# Mobile Use Agent

在火山引擎**云手机**上执行 AI Agent 任务：让 AI 帮你操作 Android 手机里的 App——打开小红书搜索、下单、看地图、查桌面……支持一键全局命令 `mua`，配置一次，之后只需描述任务。

> 本包同时是**标准 WorkBuddy Skill**（`SKILL.md` 定义触发与工作流，WorkBuddy 可自动识别调用）和**独立 CLI 应用**。

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

## 首次使用前需要准备

| 准备项 | 在哪获取 |
|---|---|
| 火山引擎账号（实名认证） | console.volcengine.com 注册 |
| AK / SK | 控制台 → 右上角头像 → 访问密钥 |
| 跨服务授权（一次性） | [点击授权 ServiceName=ipaas](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas) |
| 云手机 ProductId / PodId | 云手机控制台 → 实例列表 |

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

## 高级用法

### 命令行直接传参（跳过向导，适合脚本）

```bash
mua run --product-id PID --pod-id POD --prompt "打开微信" --gps --no-interactive
```

### 编程式调用

```python
from mobile_use_agent import MobileUseAgentClient
from credential_store import load_credentials

ak, sk = load_credentials()
client = MobileUseAgentClient(ak=ak, sk=sk)
result = client.run_and_wait(
    run_name="my-task", product_id="PID", pod_id="POD",
    user_prompt="打开微信", gps_info=None,
)
```

更多示例见 [scripts/examples.py](scripts/examples.py)。

### 目录结构

```
mobile-use-agent/
├── SKILL.md               # Skill 入口: 触发场景 + 安全边界 + 工作流
├── bin/mua                # 全局命令入口
├── install.sh             # 一键安装 mua
├── scripts/               # 可执行代码
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
A: 未完成跨服务授权。点 [这里](https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas) 授权后重试。

**Q: 找不到 ProductId / PodId？**
A: 云手机控制台 → 实例列表可查看。找到后 `mua setup` 保存为默认手机，之后不用再找。

**Q: 报 `InvalidAccessKey`？**
A: 凭证无效或过期，运行 `mua setup` 重新配置。

完整错误码表与处理见 [references/error_codes.md](references/error_codes.md)。

## 许可证

MIT
