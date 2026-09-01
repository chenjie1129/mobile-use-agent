# 云手机控制面与 Agent 协议

## 目标

控制面负责准备和维护 MUA 的执行环境，不参与 GUI Agent 的屏幕理解与操作
规划。普通任务必须先解析设备，再进入 `RunAgentTaskOneStep`。

## 设备解析状态

| status | 含义 | Agent 下一步 |
|---|---|---|
| `ready` | Product 和运行中 Pod 唯一确定 | 发起 MUA 任务 |
| `credentials_required` | 当前进程无 AK/SK | 请求凭证代理注入环境变量 |
| `product_required` | 没有 MUA 业务 | 引导用户到控制台创建业务 |
| `product_selection_required` | 存在多个业务 | 展示候选并请求选择 |
| `pod_creation_required` | 业务下没有 Pod | 展示资源、规格、机房并请求确认 |
| `pod_configuration_required` | 创建参数不完整 | 请求缺失字段 |
| `pod_selection_required` | 存在多个可选 Pod | 展示候选并请求选择 |
| `pod_not_found` | 指定 Pod 不属于业务 | 请求重新选择 |
| `power_on_required` | Pod 未运行 | 请求 `PowerOnPod` 确认 |
| `confirmation_required` | P1/P2 缺少确认令牌 | 请求用户确认指定 Action |
| `provisioning` | 创建或开机请求已提交 | 等待后重新解析 |

## 风险分级

- P0：`List*`、`Get*`、`Detail*` 等只读查询，可直接执行。
- P1：开关机、重启、应用安装/启停、备份恢复、录屏、代理配置。
- P2：创建/删除/重置/迁移、订购退订、文件传输、ADB、任意命令。
- 未登记 Action 默认 P2。

P1/P2 只有在 `confirmation_token == action` 时执行。确认令牌必须来自当前
用户意图，禁止 Agent 自行补齐。

## 标准调用顺序

```text
resolve-device
  -> ready: run
  -> selection_required: 请求用户选择后重试
  -> product_required: 用户在控制台创建业务
  -> pod_creation_required: 展示候选配置并请求确认
  -> provisioning: 等待后重试 resolve-device
```

创建业务涉及服务协议，当前保持控制台人工路径。Pod 创建可通过
`CreatePodOneStep` 完成；资源不足时订购可能产生费用，必须独立确认
`SubscribeResourceAuto`，不得与普通任务请求合并授权。

## 安全要求

- AK/SK 只能来自环境变量或凭证代理。
- 不输出 Authorization、SecretKey 或完整预签名 URL。
- 不向内层 GUI Agent 暴露 P2 原子工具。
- 所有变更动作记录 Action、ProductId、PodId、确认来源和 API TraceId。
