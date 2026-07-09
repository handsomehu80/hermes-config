# /oneplusn:edit — 编辑数字员工配置

<task>
修改已有数字员工的配置信息，如角色、Gateway 端口、状态、Agent 类型等。
</task>

<context>
## 使用场景

- 修改 Gateway 端口（冲突时）
- 暂停/恢复员工
- 更改角色
- 更新 GitHub 信息

## 参数

`$ARGUMENTS` — 可选，`--work-dir <目录> --name <员工名> --field <字段> --value <新值>`

如果未提供完整参数，进入交互式编辑。
</context>

<instructions>
## 步骤 1：选择员工

读取 handoff.yaml，列出所有员工。支持 `$ARGUMENTS --name` 直接指定。

## 步骤 2：展示当前配置

```
dev-01 当前配置：
  role: developer
  agent_type: hermes
  github_username: myteam-dev-01
  github_email: boss+dev01@example.com
  gateway_port: 8100
  status: active
  soul_source: agency-agents-zh/engineering/software-engineer/SOUL.md
  cron_frequency: */30 * * * *
  upgrade_modules:
    - hindsight
    - search
```

## 步骤 3：选择修改字段

如果 `$ARGUMENTS` 有 `--field` 和 `--value`，直接修改。
否则交互式询问：

```
可修改字段：
  1. role — 角色（developer/reviewer/architect/...）
  2. agent_type — Agent 框架（hermes/openclaw/claude-code/cursor-agent）
  3. github_username — GitHub 用户名
  4. github_email — GitHub 邮箱
  5. gateway_port — Gateway 端口
  6. status — 状态（active/paused）
  7. cron_frequency — Cron 频率
  8. soul_source — SOUL 来源
```

特殊字段处理：
- **role**：修改后询问是否重新匹配 SOUL
- **agent_type**：如果不是 hermes，提示"即将支持"
- **gateway_port**：检查新端口是否被其他员工占用
- **status**：
  - active → 提示启动 Gateway
  - paused → 提示停止 Gateway

## 步骤 4：执行修改

更新 handoff.yaml 对应字段，记录 `metadata.updated_at`。

## 步骤 5：确认后续操作

询问：
- 是否同步 README？
- 是否需要重启 Gateway？（如果修改了 port 或 agent_type）
- 是否继续编辑其他字段？

## 输出

```
[✓] dev-01 配置已更新：
    gateway_port: 8100 → 8104
    
[⚠] Gateway 端口已变更，建议重启：
    hermes profile use dev-01 && hermes gateway restart
    
[✓] README 已同步
```
</instructions>

<output_format>
- 展示修改前后的对比
- 如果修改需要重启 Gateway，明确提示
- 如果修改涉及 SOUL 变更，提示重新匹配
</output_format>
