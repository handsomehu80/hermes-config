# /oneplusn:init — 初始化 1+N 数字员工团队

<task>
执行完整的 1+N 数字员工团队初始化流程。分三个阶段：
1. 创建子公司（org-setup skill）
2. 批量创建数字员工（onboarding skill）
3. 可选升级（upgrade skill）

所有文件生成在子公司工作目录中（以 Organization 名称命名）。
</task>

<context>
## 前置要求

- 已安装 Hermes CLI（`hermes --version`）
- 有 GitHub 账号（个人账号即可创建 Organization）
- 已安装 git、python3
- 已安装 Python PyYAML 库（`python3 -c "import yaml"` 不报错）
- 已加载三个 Skill：oneplusn-org-setup、oneplusn-agent-onboarding、oneplusn-agent-upgrade

## 本次操作将创建

1. **GitHub Organization**（子公司）
2. **老板 PAT Token**（Fine-grained，Organization 范围）
3. **GitHub 仓库**（agent_workflow，含 README + rules）
4. **N 个数字员工**（每个含 Profile + SOUL + RULES + CronJob）
5. **handoff.yaml**（团队核心配置文件）

## 工作目录

所有文件生成在 `{organization-name}/` 目录中，不与根目录冲突。
</context>

<instructions>
按以下步骤执行，每步完成后确认再继续：

## 阶段 1/3：创建子公司（调用 oneplusn-org-setup skill）

### 1.1 检测依赖

检查以下工具是否已安装：
- `hermes --version` → 未安装则提示用户先安装 Hermes CLI
- `git --version` → 未安装则提示
- `python3 --version` → 未安装则提示

### 1.2 创建 GitHub Organization

询问用户（带默认值）：
- "Organization 名称（子公司名）" → 如 `oneplusn-team`
- "老板 GitHub 用户名" → 用户的 GitHub 账号
- "老板邮箱" → 用于 Git 配置
- "仓库名称" → 默认 `agent_workflow`

使用 create_org.py 脚本创建：
```bash
python3 scripts/create_org.py --org-name $ORG_NAME --boss-username $BOSS_USERNAME --boss-email $BOSS_EMAIL --repo-name $REPO_NAME
```

创建完成后会生成 `handoff.yaml`，记录：
- organization.name
- boss.github_username、email、token
- repository.name、url

### 1.3 创建工作目录

创建 `{org-name}/` 目录结构：
```
{org-name}/
├── handoff.yaml          # 从 create_org.py 生成，移到此处
├── README.md             # 后续生成
├── rules.md              # 从 onboarding skill 复制 rules-template.md
└── agents/               # 空目录，后续员工文件放这里
```

复制 rules-template.md 到工作目录：
```bash
cp oneplusn-agent-onboarding/references/rules-template.md {org-name}/rules.md
```

更新 handoff.yaml 的 metadata.stage 为 `org-setup-complete`。

## 阶段 2/3：创建数字员工（循环调用 oneplusn-agent-onboarding skill）

询问用户："需要创建多少个数字员工？" → 默认 1

对每个数字员工执行：

### 2.1 选择 Agent 框架类型

询问（带选项）：
```
选择 Agent 框架类型：
1. Hermes Agent（当前唯一支持）★ 默认
2. OpenClaw（即将支持）
3. Claude Code（即将支持）
4. Cursor Agent（即将支持）
```

如果选非 Hermes，提示"即将支持，将使用 Hermes Agent"并记录用户意向。

### 2.2 执行上岗（调用 onboard_agent.py）

```bash
python3 scripts/onboard_agent.py --handoff {org-name}/handoff.yaml --interactive
```

交互式引导包含：
1. 选择角色（8选1：developer、reviewer、architect、tester、project-manager、insight-specialist、research-analyst、security-engineer）
2. 输入员工名字（默认根据角色生成，如 `dev-01`）
3. GitHub 账号配置：
   - GitHub 账号配置（提供 5 种选项）：
     - **[A] 已有账号** — 直接输入用户名/邮箱/Token
     - **[B] 引导创建** — 显示完整的 GitHub 注册教程（含 + 别名邮箱方法）
     - **[C] + 别名邮箱** — 用老板邮箱的 + 别名创建（推荐，无需注册新邮箱）
     - **[D] 复用 Token** — 员工与老板共享 Token（快速但不推荐）
     - **[Q] 跳过** — 稍后手动配置
   - PAT Token 创建也有详细教程引导（Fine-grained，权限：Contents/Issues/PR read+write）
4. Hermes Profile 配置：
   - 使用 `hermes --clone` 创建隔离 Profile
   - 配置 gateway port（自动分配，默认 8100 起）
5. SOUL 灵魂注入：
   - 从 agency-agents-zh 仓库读取对应角色的 SOUL.md
   - 交互式确认：匹配成功？→ y 直接使用 / n 编辑 / 搜索其他角色
   - 支持搜索关键词找匹配角色
6. RULES 铁律：
   - 将 rules-template.md 写入员工 Profile 的 RULES.md
   - 包含 6 条铁律（Assignee 两步走、换人先写 comment 等）
7. README 入职 3 问：
   - "遇到不确定的需求怎么办？" → 默认：先问老板，不猜
   - "代码审查不通过怎么办？" → 默认：写 comment 说明问题，等对方修复
   - "任务完成后做什么？" → 默认：comment 总结 + 改 assignee 给审查员
8. CronJob 配置：
   - 默认每 30 分钟轮询 Issues
   - 询问是否自定义频率
   - 生成启动/停止命令

### 2.3 更新 handoff.yaml

每完成一个员工，更新 handoff.yaml：
```yaml
agents:
  {name}:
    role: developer
    agent_type: hermes
    github_username: xxx
    github_email: xxx@users.noreply.github.com
    gateway_port: 8100
    status: active
    onboarded_at: 2026-06-04T10:00:00
    soul_source: agency-agents-zh/engineering/...
```

### 2.4 询问继续

完成一个后询问："是否继续创建下一个？" → y 继续 / n 结束阶段 2

## 阶段 3/3：可选升级（调用 oneplusn-agent-upgrade skill）

询问："是否升级数字员工能力？" → y 进入 / n 跳过

如果升级，对每个员工询问升级模块（多选）：
- hindsight — Hindsight 记忆系统（默认开启）
- search — 搜索感知增强
- voice — 语音交互
- efficiency — 效率优化

调用 upgrade_agent.py：
```bash
python3 scripts/upgrade_agent.py --handoff {org-name}/handoff.yaml --name {agent-name} --modules hindsight,search
```

更新 handoff.yaml 记录升级状态。

## 收尾：同步 README

生成 README.md 并提交到 GitHub：
1. 读取 handoff.yaml 中的团队信息
2. 使用 readme-template.md 模板生成完整 README
3. 包含：Mermaid 协作图、团队表格、核心规则、标签说明、Cronjob 配置
4. 提交到 GitHub 仓库

更新 handoff.yaml metadata.stage 为 `team-ready`。

## 最终输出

```
========================================
  ✅ 1+N 数字员工团队初始化完成！
========================================

📁 工作目录: {org-name}/
🏢 Organization: {org-name}
📦 仓库: {org-name}/agent_workflow
👤 老板: {boss_username}
👥 数字员工: {N} 个
   - dev-01 (developer) [hermes] port:8100
   - rev-01 (reviewer) [hermes] port:8101
   ...

📋 下一步：
   1. 每个员工运行 Gateway：hermes profile use {name} && hermes gateway start
   2. 创建 Issue 测试任务流转
   3. 查看状态：/oneplusn:status --work-dir {org-name}/

========================================
```
</instructions>

<output_format>
输出格式：
- 阶段标题用 `[阶段 X/3]` 标记
- 每步操作前输出 `[→] 步骤说明`
- 成功用 `[✓]`，警告用 `[⚠]`，错误用 `[✗]`
- 最终输出总结表格
</output_format>

<human_review_needed>
以下决策需要用户确认：
- [ ] Organization 名称是否符合预期
- [ ] 创建的 GitHub Organization 是否公开/私有
- [ ] PAT Token 的权限范围是否足够
- [ ] 每个员工的 gateway port 是否与本地其他服务冲突
- [ ] CronJob 频率是否合理（默认 30 分钟）
</human_review_needed>
