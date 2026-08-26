# 命令参考 (CLI)

所有命令通过 `scripts/cli.py` 执行，自动加载本地凭证（`~/.mobile_use_agent/credentials.json`）。

## 凭证管理

```sh
python3 scripts/cli.py setup              # 配置/重新配置 AK/SK (SK 输入不回显)
python3 scripts/cli.py whoami             # 查看当前凭证状态 (脱敏展示, 只读)
python3 scripts/cli.py logout             # 删除本地保存的凭证
```

首次运行任意命令时会自动引导配置 AK/SK。

## 任务操作

```sh
# 运行任务 (交互式输入 ProductId/PodId/提示词)
python3 scripts/cli.py run

# 直接传参 (跳过交互)
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "打开微信"

# 完整参数
python3 scripts/cli.py run --product-id PID --pod-id POD --prompt "..." \
    --run-name my-task --max-step 100 --timeout 300 --system-prompt "..." \
    --gps --no-interactive

# 查询 / 结果 / 取消 / 列表
python3 scripts/cli.py status --run-id RUN_XXX
python3 scripts/cli.py result --run-id RUN_XXX
python3 scripts/cli.py cancel --run-id RUN_XXX
python3 scripts/cli.py list [--run-id RUN_XXX] [--run-name NAME] [--page-size N] [--page-number N]
```

## 代理运行配置管理

```sh
python3 scripts/cli.py config-create       # 创建代理运行配置
python3 scripts/cli.py config-list         # 查询配置列表
python3 scripts/cli.py config-delete       # 删除配置
```

## 快速脚本与示例

```sh
python3 scripts/run.py                     # 最简快速运行 (仅交互输入必要参数)
python3 scripts/examples.py                # 5 个编程式调用场景示例
python3 scripts/geo.py                     # 单独测试定位 (输出来源/坐标/GpsInfo)
```

## 凭证优先级

命令行 `--ak/--sk` > 环境变量 `VOLC_ACCESSKEY`/`VOLC_SECRETKEY` > 本地凭证文件。

## 任务过程实时打印

运行任务时步骤**实时增量打印**（每步只出现一次）：

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

- `[OK]` = 步骤成功（StepResult.IsSuccess=true），`[FAIL]` = 失败
- 任务结束后自动拉取最终结果（状态/内容/截屏 TOS URL/用量）
- 任务失败自动归因：打印失败原因、操作建议、错误码

## 交互式菜单

```sh
python3 scripts/cli.py     # 无参数进入菜单: 运行/状态/结果/取消/列表/配置管理
```

## 非交互模式

`--no-interactive` 跳过交互式参数确认；`--gps` 显式授权定位注入（此时不询问）。
