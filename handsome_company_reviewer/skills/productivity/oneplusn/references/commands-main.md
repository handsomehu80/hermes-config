# /oneplusn — 1+N 数字员工团队管理

<task>
你是 1+N 数字员工团队的管理助手。当用户输入 /oneplusn 或 /oneplusn help 时，展示完整的命令帮助信息和系统概览。
</task>

<context>
1+N 数字员工团队是一套本地化的 AI Agent 协作方案：
- 1 个老板（用户自己）+ N 个数字员工（AI Agent）
- 每个员工有独立 GitHub 账号、Hermes Agent Profile、角色灵魂（SOUL）、协作铁律（RULES）
- 通过 GitHub Issues 分配任务，员工自动轮询领取
- 所有文件生成在子公司工作目录中（以 Organization 名称命名）

三个 Skill 协同工作：
1. **oneplusn-org-setup**：创建子公司 + 老板账号 + Organization + 仓库
2. **oneplusn-agent-onboarding**：逐个创建数字员工（Profile + SOUL + RULES + Cron）
3. **oneplusn-agent-upgrade**：升级数字员工能力（Hindsight + 搜索 + 语音 + 效率）
</context>

<instructions>
输出以下帮助信息（用中文）：

## /oneplusn — 1+N 数字员工团队管理

> 一条命令管理你的 AI 数字员工团队：开公司、招员工、升级能力、日常运维。

### 可用子命令

| 命令 | 说明 | 对应 Skill |
|------|------|-----------|
| `/oneplusn:init` | 初始化整个团队（创建子公司 + 批量招员工 + 可选升级） | org-setup + onboarding + upgrade |
| `/oneplusn:add` | 添加单个数字员工 | onboarding |
| `/oneplusn:upgrade` | 升级数字员工能力 | upgrade |
| `/oneplusn:status` | 查看所有数字员工状态 | — |
| `/oneplusn:sync` | 同步 README 到 GitHub 仓库 | — |
| `/oneplusn:delete` | 删除/停用数字员工 | — |
| `/oneplusn:edit` | 编辑数字员工配置 | — |

### 快速开始

```
# 第 1 步：初始化（交互式创建整个团队）
/oneplusn:init

# 第 2 步：后续添加员工
/oneplusn:add

# 第 3 步：升级员工能力
/oneplusn:upgrade
```

### 工作目录结构

每个子公司独立一个目录（以 Organization 名称命名）：

```
{org-name}/                    # 子公司工作目录
├── handoff.yaml              # 团队核心配置（子公司 + 老板 + 所有员工）
├── README.md                 # 团队 README（自动同步到 GitHub）
├── rules.md                  # Agent 协作铁律
└── agents/                   # 各数字员工的本地文件
    └── {name}/
        ├── soul.md           # 角色灵魂定义
        └── notes.txt         # 备注
```

### 支持的数字员工角色

- `developer` — 高级开发工程师
- `reviewer` — 代码审查员
- `architect` — 架构师
- `tester` — 测试工程师
- `project-manager` — 项目经理
- `insight-specialist` — 洞察分析师
- `research-analyst` — 研究分析师
- `security-engineer` — 安全工程师

### 支持的 Agent 框架

- ✅ **Hermes Agent**（当前完全支持）
- 🔜 OpenClaw（即将支持）
- 🔜 Claude Code（即将支持）
- 🔜 Cursor Agent（即将支持）

---
*提示：输入 `/oneplusn:init` 开始创建你的数字员工团队。*
</instructions>
