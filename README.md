# Mobile Use Agent — 火山引擎云手机 Agent Skill

调用火山引擎 **Mobile Use Agent OpenAPI** 在云手机上执行 AI Agent 任务（UI 自动化操作 Android App），封装为**标准 WorkBuddy Skill**。

## 这是什么

一个同时具备两种身份的包：

1. **标准 Skill**（主身份）— `SKILL.md` 定义触发场景与工作流，WorkBuddy 通过描述自动识别、按需调用；安装到 `~/.workbuddy/skills/` 后可用 skill 机制管理。
2. **可独立运行的 CLI 应用** — 直接 `python3 scripts/cli.py ...` 手动使用，无需经过 skill 调度。

## 目录结构

```
mobile-use-agent/
├── SKILL.md               # Skill 入口: frontmatter + 触发场景 + 安全边界 + 工作流
├── scripts/               # 可执行代码 (全部 Python 模块)
│   ├── cli.py             # 交互式 CLI + 命令行模式 (主入口)
│   ├── run.py             # 快速运行脚本 (最简模式)
│   ├── examples.py        # 编程式调用示例 (5 个场景)
│   ├── mobile_use_agent.py  # 核心客户端类, 封装 10 个 API
│   ├── error_codes.py     # 错误码定义与解析 (公共 12 + 业务 32 + 认证 5)
│   ├── credential_store.py  # AK/SK 凭证持久化 (~/.mobile_use_agent/)
│   └── geo.py             # 本地地理位置获取 (CoreLocation + IP 降级)
├── references/            # 按需加载的参考文档
│   ├── commands.md        # 命令参考
│   ├── error_codes.md     # 错误码参考
│   ├── gps.md             # GPS 定位注入参考
│   └── api_reference.md   # OpenAPI 接口与参数参考
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量配置模板 (可选)
└── README.md              # 本文档
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 首次配置凭证 (只需一次, SK 输入不回显)
python3 scripts/cli.py setup

# 3. 运行任务 (每次输入 ProductId/PodId/提示词)
python3 scripts/cli.py run
```

凭证策略：

| 参数 | 配置时机 | 说明 |
|---|---|---|
| **AK / SK** | 首次运行时配置一次 | 保存到 `~/.mobile_use_agent/credentials.json`（权限 600），后续自动加载 |
| **ProductId** | 每次发起任务时输入 | 云手机业务 ID |
| **PodId** | 每次发起任务时输入 | 云手机实例 ID |
| **用户提示词** | 每次发起任务时输入 | 想让 Agent 执行的操作 |
| **GPS 定位授权** | 每次发起任务时询问 | 允许后获取当前位置注入 GpsInfo，拒绝则不注入 |

## 以 Skill 方式使用

- **安装**: 将本目录复制到 `~/.workbuddy/skills/mobile-use-agent/`（或直接在此目录开发后同步）
- **触发**: WorkBuddy 根据 `SKILL.md` 的 description 自动识别——当用户要求"在云手机上打开 X / 执行 Y"时自动加载
- **调用**: 按 `SKILL.md` 工作流执行 `scripts/cli.py run ...`，细节查 `references/`

## 以 CLI 方式使用

```bash
python3 scripts/cli.py setup              # 配置/重新配置 AK/SK
python3 scripts/cli.py whoami             # 查看当前凭证状态
python3 scripts/cli.py run                # 运行任务 (交互式)
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "打开微信" --gps
python3 scripts/cli.py status --run-id RUN_XXX
python3 scripts/cli.py result --run-id RUN_XXX
python3 scripts/cli.py cancel --run-id RUN_XXX
python3 scripts/cli.py list
python3 scripts/cli.py                    # 交互式菜单
```

完整命令与参数见 `references/commands.md`。

## 关键特性

- **任务过程实时打印**: 步骤增量输出，失败自动归因（原因/建议/错误码）
- **GPS 定位注入**: CoreLocation（米级）→ IP 定位（城市级）自动降级，每次询问用户授权
- **错误码适配**: 双通道捕获（HTTP 200 业务错误 + ApiException），统一 `MobileUseError`
- **凭证安全**: 本地文件权限 600、展示脱敏、输入不回显、优先级 参数 > 环境变量 > 文件

## 前置条件

1. 火山引擎账号（实名认证）
2. AK/SK（控制台 → 访问密钥）
3. 跨服务授权 `ServiceName=ipaas`（https://console.volcengine.com/iam/service/attach_role/?ServiceName=ipaas）
4. 云手机业务 (ProductId) 和实例 (PodId)
5. (可选) TOS 存储桶（截图/录屏持久化）

## 许可证

MIT
