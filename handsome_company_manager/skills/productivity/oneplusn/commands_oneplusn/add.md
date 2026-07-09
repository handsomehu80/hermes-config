# /oneplusn:add — 添加单个数字员工

<task>
在已有团队中新增一个数字员工。加载 oneplusn-agent-onboarding skill，执行单个员工的完整上岗流程。
</task>

<context>
## 使用场景

- 初始化后想增加新员工
- 需要特定角色处理专项任务（如安全审计、市场调研）
- 替换离职员工（删除旧 + 创建新）

## 前置要求

- 已完成 `/oneplusn:init`，存在 `{org-name}/handoff.yaml`
- 已加载 oneplusn-agent-onboarding skill

## 参数

`$ARGUMENTS` — 可选，格式：`--work-dir <目录> --role <角色> --name <名字>`

如果未提供参数，进入交互式引导。
</context>

<instructions>
## 步骤 1：定位工作目录

如果 `$ARGUMENTS` 包含 `--work-dir`，使用该目录。
否则交互式询问：
- "工作目录路径（如 oneplusn-team/）" → 列出当前目录下的候选文件夹
- 如果只有一个 handoff.yaml 所在的目录，直接使用并提示

检查 `handoff.yaml` 是否存在，不存在则提示先运行 `/oneplusn:init`。

## 步骤 2：选择 Agent 框架类型

询问（带选项）：
```
选择 Agent 框架类型：
1. Hermes Agent（当前唯一支持）★ 默认
2. OpenClaw（即将支持）
3. Claude Code（即将支持）
4. Cursor Agent（即将支持）
```

如果选非 Hermes，提示"即将支持，将使用 Hermes Agent"并记录用户意向到 `handoff.yaml`。

## 步骤 3：选择角色

列出 8 个可选角色（带编号和说明）：

| 编号 | 角色 | 说明 | 默认名字 |
|------|------|------|----------|
| 1 | developer | 高级开发工程师 | dev-0{N+1} |
| 2 | reviewer | 代码审查员 | rev-0{N+1} |
| 3 | architect | 架构师 | arch-0{N+1} |
| 4 | tester | 测试工程师 | test-0{N+1} |
| 5 | project-manager | 项目经理 | pm-0{N+1} |
| 6 | insight-specialist | 洞察分析师 | insight-0{N+1} |
| 7 | research-analyst | 研究分析师 | research-0{N+1} |
| 8 | security-engineer | 安全工程师 | sec-0{N+1} |

根据当前已有员工数量自动推荐编号（如已有 dev-01，则推荐 dev-02）。

## 步骤 4：执行上岗（调用 onboard_agent.py）

```bash
python3 scripts/onboard_agent.py --handoff {work-dir}/handoff.yaml --interactive
```

上岗流程（交互式）：

### 4.1 GitHub 账号配置（交互式引导）

提供 5 种选项，让用户选择最适合的方式：

**[A] 已有账号** — 直接输入
- 用户名、邮箱、Token（如有）
- 如果没有 Token，显示 PAT 创建教程引导

**[B] 引导创建新账号** — 完整的分步教程
- 详细展示 GitHub 注册流程（signup → 邮箱 → 用户名 → 验证 → Free 计划）
- 包含 + 别名邮箱的使用方法说明
- 自动建议用户名格式：`{org-name}-{name}`
- 用户创建完成后回来继续

**[C] + 别名邮箱创建（推荐）**
- 如果用老板邮箱 `xxx@163.com`，自动建议 `xxx+dev02@163.com`
- 无需注册新邮箱，+ 别名邮件会转发到原邮箱
- 自动建议用户名，用户确认后生成完整的注册步骤

**[D] 复用老板 Token**
- 快速但不推荐（共享 Token 会导致 API 限流、操作记录混淆）
- 需用户确认风险提示

**[Q] 跳过**
- 稍后手动配置

**PAT Token 获取**
无论哪种方式，如果没有 Token，都会显示详细的创建教程：
1. Settings → Developer settings → Fine-grained tokens
2. 权限必须勾选：Contents(rw)、Issues(rw)、Pull requests(rw)
3. ⚠️ Token 只能看一次，立即保存

### 4.2 Hermes Profile 配置

```bash
# 创建隔离 Profile
hermes profile create {name} --from default

# 或克隆现有
hermes profile clone default {name}
```

Gateway 端口自动分配：从 8100 起，检查 handoff.yaml 中已用端口，取下一个可用端口。

### 4.3 SOUL 灵魂注入

从 agency-agents-zh 仓库匹配角色 SOUL.md：

```
[→] 正在从 agency-agents-zh 匹配角色灵魂...

角色: developer
匹配文件: agency-agents-zh/engineering/software-engineer/SOUL.md
匹配度: 95%

SOUL 内容预览（前 500 字）：
---
{预览内容}
---

确认使用该 SOUL？
[y] 是 — 直接使用
[n] 否 — 搜索其他角色
[e] 编辑 — 自定义修改
```

如果选择编辑，打开编辑器让用户修改后保存。

如果选择搜索，询问关键词，在 agency-agents-zh 中搜索匹配的角色 SOUL.md。

将最终确认的 SOUL.md 内容写入员工 Profile 目录。

### 4.4 RULES 铁律

将 `rules-template.md` 写入员工目录的 `RULES.md`。

铁律内容包括：
1. Assignee 两步走：干完先 comment 总结 → 再改 assignee 交给下一个人
2. 换人先写 comment：assignee 变更必须伴随 comment 说明交接内容
3. 新反馈检测：运行中检测到新 feedback 时，优先处理新反馈而非继续原任务
4. 关闭权限：只有审查员有权 close Issue，开发只能 comment + 移交
5. 中文 comment：所有 Issue Comment 必须使用中文
6. 标签管理：项目经理负责打标签，其他人只读

### 4.5 README 入职 3 问

向员工提出 3 个入职问题，生成默认答案（可编辑）：

**Q1**: "遇到不确定的需求怎么办？"
- 默认答案：先问老板确认，绝不猜测。在 comment 中列出不确定点 @老板。

**Q2**: "代码审查不通过怎么办？"
- 默认答案：在 comment 中详细说明问题点，等对方修复后重新审查。不直接修改他人代码。

**Q3**: "任务完成后做什么？"
- 默认答案：
  1. 写 comment 总结做了什么、改了哪些文件
  2. 如果自己是开发，assignee → 改给审查员
  3. 如果自己是审查员，assignee → 改给老板等终审
  4. 不自己 close Issue

### 4.6 CronJob 配置

生成定时轮询任务：

```bash
# 默认：每 30 分钟轮询一次
*/30 * * * * cd {work-dir} && gh issue list --repo {org}/{repo} --assignee {github-username} --state open --json number,title,body,comments > /tmp/issues-{name}.json && hermes profile use {name} && hermes run /tmp/issues-{name}.json
```

询问是否自定义频率，提供选项：
- 10 分钟（高频）
- 30 分钟（默认）
- 1 小时（低频）
- 自定义 cron 表达式

生成启动/停止快捷命令脚本到 `{work-dir}/agents/{name}/start.sh` 和 `stop.sh`。

## 步骤 5：更新 handoff.yaml

添加新员工记录：
```yaml
agents:
  {name}:
    role: developer
    agent_type: hermes
    github_username: xxx
    github_email: xxx@users.noreply.github.com
    gateway_port: 8101
    status: active
    onboarded_at: 2026-06-04T12:00:00
    soul_source: agency-agents-zh/engineering/software-engineer/SOUL.md
    cron_frequency: "*/30 * * * *"
```

更新 `metadata.updated_at`。

## 步骤 6：同步 README

询问："同步更新 README？" → 默认 y

重新生成 README.md 并提交到 GitHub。

## 输出

```
[✓] 数字员工 {name} 上岗成功！
    角色: {role}
    GitHub: {username}
    Agent: Hermes
    Profile: {name}
    Gateway: port {port}
    SOUL: {soul_source}
    Cron: 每 30 分钟

[→] 启动命令: ./{work-dir}/agents/{name}/start.sh
[→] 查看状态: /oneplusn:status --work-dir {work-dir}/
```
</instructions>

<output_format>
- 每步操作前输出 `[→] 步骤说明`
- 成功用 `[✓]`，警告用 `[⚠]`，错误用 `[✗]`
- 最终输出员工信息卡片
</output_format>

<example>
用户输入：/oneplusn:add --work-dir oneplusn-team/ --role security-engineer

输出示例：
[→] 工作目录: oneplusn-team/
[✓] 找到 handoff.yaml，当前 3 个员工
[→] Agent 框架: Hermes Agent
[→] 角色: security-engineer（安全工程师）
[→] 推荐名字: sec-01
[→] GitHub 账号配置...
[→] Hermes Profile 创建...
[✓] Profile sec-01 已创建
[→] SOUL 灵魂注入...
[✓] 匹配: agency-agents-zh/engineering/security-engineer/SOUL.md
[→] RULES 铁律写入...
[→] README 入职 3 问...
[→] CronJob 配置...
[✓] handoff.yaml 已更新
[✓] README 已同步

========================================
  ✅ 数字员工 sec-01 上岗成功！
========================================
角色: security-engineer
GitHub: myteam-sec-01
Agent: Hermes
Gateway: port 8103
========================================
</example>

<human_review_needed>
- [ ] Gateway 端口是否与本地其他服务冲突
- [ ] PAT Token 权限是否足够
- [ ] SOUL 内容是否匹配预期角色
- [ ] Cron 频率是否合理
</human_review_needed>
