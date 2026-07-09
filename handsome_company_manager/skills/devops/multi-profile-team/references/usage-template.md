# USAGE.md Template (Team Manual)

Copy this to `~/AppData/Local/hermes/USAGE.md` and edit for your team. The structure below is the one that worked for the 4-profile team in the case study. Sections can be added/removed; the order is the order a new user should encounter them.

```markdown
# Hermes Agent Team — 使用指导书

> <N>-profile agent team (<roster>) usage manual. Based on <date> validation.

---

## 0. 快速上手 (30 秒)

\`\`\`bash
# 1. 启动 PM (交互模式)
hermes -p pm

# 2. 在 PM 提示符下, 直接说需求
> <example user request>

# 3. PM 自动拆解任务, 派给 <specialists>, 完成后向你汇报
\`\`\`

或者手动控制 (高级用户):

\`\`\`bash
hermes kanban create "任务标题" --assignee eng --body "详细描述..."
hermes kanban list    # 看进度
hermes kanban tail <id>   # 实时日志
\`\`\`

---

## 1. 团队结构

<ASCII diagram or table showing the team layout>

**N 个角色:**

| Profile | 角色 | 职责 | 主要工具 | 何时被派单 |
|---------|------|------|---------|------------|
| pm      | PM  | <职责> | <工具> | <场景> |
| eng     | 工程师 | <职责> | <工具> | <场景> |
| qa      | 测试 | <职责> | <工具> | <场景> |
| ast     | 助理 | <职责> | <工具> | <场景> |

**profile 目录结构:**

\`\`\`
C:\\Users\\<user>\\AppData\\Local\\hermes\\profiles\\
├── <name>\\
│   ├── config.yaml      # 独立配置
│   ├── .env             # API 密钥
│   ├── SOUL.md          # 人格/工作守则
│   ├── memories\\        # 记忆
│   ├── skills\\          # 加载的技能
│   └── logs\\            # 运行日志
\`\`\`

---

## 2. 与团队协作的 3 种方式

### 方式 A: 对 PM 说话 (推荐, 90% 场景)

\`\`\`bash
hermes -p pm
\`\`\`

PM 会自动: 理解需求, 拆解为 Kanban 卡片, 设置依赖, 派给合适的角色, 完成后汇总。

### 方式 B: 手动派单 (PM 流程可见, 学习用)

\`\`\`bash
# 单任务
hermes kanban create "标题" --assignee <who> --body "..."

# 父子链 (T1 → T2)
T1=$(hermes kanban create "T1: 调研" --assignee ast --body "..." --json | jq -r .task_id)
hermes kanban create "T2: 实现" --assignee eng --parent $T1 --body "..."

# 完整 4 段 (T1 → T2 → T3 → T4) — see templates/4card-chain.sh
\`\`\`

### 方式 C: 直接和某个角色对话 (紧急/特定场景)

\`\`\`bash
hermes -p eng   # 直接和工程师对话
hermes -p qa    # 直接和测试对话
hermes -p ast   # 直接和助理对话
\`\`\`

---

## 3. Kanban 看板命令速查

\`\`\`bash
# === 任务管理 ===
hermes kanban create TITLE --assignee WHO --body "..."
hermes kanban create TITLE --parent T1_ID --parent T2_ID   # 多父依赖
hermes kanban list
hermes kanban show <ID>
hermes kanban tail <ID>           # 实时日志 (可能超时)
hermes kanban edit <ID>

# === 任务流转 ===
hermes kanban assign <ID> <PROFILE>      # 改派
hermes kanban reclaim <ID>               # 强制重跑 (卡死时)
hermes kanban reassign <ID> <NEW>        # 转给别的 profile
hermes kanban unblock <ID> --reason "..."  # 解锁 blocked 任务
hermes kanban block <ID> <REASON>        # 手动 block
hermes kanban complete <ID> --summary "..."  # 手动 complete
hermes kanban archive <ID>               # 归档
hermes kanban promote <ID>               # todo → ready

# === 视图与统计 ===
hermes kanban stats
hermes kanban boards
hermes kanban runs <ID>      # 执行历史
hermes kanban log <ID>       # 详细事件流

# === 调度器 ===
hermes kanban daemon                     # 前台 daemon
hermes kanban daemon --interval 30       # 30s tick
hermes kanban dispatch                   # 手动触发 tick
hermes kanban watch                      # 实时 watch 看板
\`\`\`

---

## 4. 实战案例: <your case>

<describe the validation task you ran — what was built, what cards, what timings, what artifacts>

---

## 5. 关键概念与陷阱 (踩过的坑)

### 5.1 依赖关系: \`--parent\` 的语义

正确: 父任务 done → 子任务 ready → 调度器派单

陷阱: 不要先建子任务再 link, 会留出「父未完成、子已被派」的窗口。

### 5.2 eng 用 \`kanban_block(review-required)\` 会卡住流程

<describe the parent-link trap — see kanban-orchestrator skill pitfalls>

解决 (二选一):
1. 修改 eng SOUL.md: 用 \`kanban_complete\` + comment marker (推荐)
2. PM 手动 unblock (浪费 150s 重 spawn)

### 5.3 Profile 路径硬编码

Hermes 配置文件/记忆/SOUL.md 在:
\`\`\`
%LOCALAPPDATA%\\hermes\\profiles\\<name>\\
\`\`\`

修改这些文件不需要重启 gateway, 下次该 profile 启动时生效。

### 5.4 工具集差异化

每个 profile 的工具集是独立的, 在:
\`\`\`
%LOCALAPPDATA%\\hermes\\profiles\\<name>\\config.yaml
\`\`\`
下的 \`agent.disabled_toolsets\` 字段。

重要: 修改后需要新会话 (\`/reset\` 或退出重进) 才生效。

### 5.5 Gateway 重启需要明确批准

\`hermes gateway restart\` 在 smart 审批模式下被拦截。
绕过: 不依赖 gateway 集成用独立 daemon, 接受 smart 拦截, 改用 \`approvals.mode: off\`

### 5.6 Dispatcher tick 时间

默认 60s。
调整: \`hermes config set kanban.dispatch_interval_seconds 30\`

### 5.7 失败上限

默认 \`kanban.failure_limit: 2\`。
调整: \`hermes config set kanban.failure_limit 3\`

---

## 6. 进阶用法

### 6.1 任务重试与恢复

\`\`\`bash
hermes kanban reclaim <ID>                          # 卡死时
hermes kanban reassign <ID> <NEW_PROFILE>           # 调换 profile
hermes -p eng model --set <new-model>               # 改模型后
hermes kanban reclaim <ID>                          # 重试
\`\`\`

### 6.2 跨平台通知 (可选)

任务完成时推到 Slack/Telegram/Discord:
\`\`\`bash
# 在 .env 加平台 token
SLACK_BOT_TOKEN=xoxb-....
# 重启 gateway 后, 完成事件自动推送
hermes gateway restart
\`\`\`

### 6.3 持久 Workspace (worktree)

代码任务推荐用 git worktree:
\`\`\`bash
hermes kanban create "..." --assignee eng --workspace worktree --branch wt/feature-x
\`\`\`

### 6.4 Memory 隔离

每个 profile 独立记忆:
\`\`\`bash
hermes -p pm memory status
hermes -p eng memory status
\`\`\`

跨 profile 共享信息: 在 \`kanban_comment\` 里写, 不要写到 memory。

---

## 7. 维护任务清单

### 每周
\`\`\`bash
hermes kanban stats
hermes kanban list --status done | tail -20
hermes kanban archive <ID>
hermes skills update
\`\`\`

### 每月
\`\`\`bash
hermes doctor
hermes backup
ls -lh ~/AppData/Local/hermes/kanban.db
\`\`\`

### 故障排查

| 症状 | 排查 |
|------|------|
| 任务一直 ready 不跑 | \`hermes kanban dispatch\` 手动触发; 看 gateway 日志 |
| Worker spawn 后无输出 | \`hermes kanban tail <ID>\`; profile 模型或密钥问题 |
| eng 完成代码但 qa 不开始 | 父任务被 block, 需要 unblock (见 5.2) |
| 任务永远不 done | 看 \`runs\` 字段, max_runtime 触发, 调大 |
| Gateway 重启被拒 | smart 模式拦截, 手动批准或换 mode |

---

## 8. 参考命令 (粘到终端随时用)

\`\`\`bash
# === Profile 管理 ===
hermes profile list
hermes profile show pm
hermes -p pm model
hermes -p pm tools list

# === Kanban 模板 (粘即用) ===
# 见 templates/4card-chain.sh

# === 监控 ===
hermes kanban watch
hermes kanban list | grep running
hermes kanban tail <ID>
\`\`\`

---

## 9. 附: 目录与文件速查

\`\`\`
C:\\Users\\<user>\\AppData\\Local\\hermes\\
├── config.yaml
├── .env
├── SOUL.md
├── state.db
├── kanban.db
├── kanban\\workspaces\\     # 各任务的 scratch 目录
├── profiles\\<name>\\       # 每个 profile 独立目录
├── logs\\{gateway,agent,errors}.log
├── plans\\
└── USAGE.md                # 本文档
\`\`\`

---

## 10. 端到端验证记录

<date, task, total time, per-card table, artifacts, conclusion>
```

## How to Use This Template

1. Copy to `~/AppData/Local/hermes/USAGE.md`
2. Replace `<placeholders>` with your team details
3. Add a real case study in section 4 — abstract manuals are less useful than ones that say "here's what happened when we ran it"
4. The pitfalls in section 5 should reflect what you actually hit, not what you might theoretically hit
5. Keep the troubleshooting table in section 7 short — long tables indicate you haven't actually run the team enough to know what breaks
