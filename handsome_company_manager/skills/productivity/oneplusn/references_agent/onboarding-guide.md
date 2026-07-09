# 数字员工上岗详细指南

逐个配置数字员工的完整操作步骤。

## 目录

1. [读取子公司信息](#读取子公司信息)
2. [确定 Agent 身份](#确定-agent-身份)
3. [创建 Hermes Profile](#创建-hermes-profile)
4. [绑定 GitHub](#绑定-github)
5. [注入角色灵魂（SOUL 匹配）](#注入角色灵魂)
6. [阅读团队 README](#阅读团队-readme)
7. [启动 Gateway](#启动-gateway)
8. [配置定时任务](#配置定时任务)
9. [更新 handoff.yaml](#更新-handoffyaml)

---

## 读取子公司信息

上岗前读取 `handoff.yaml`：

```yaml
organization:
  name: oneplusn-team
  url: https://github.com/oneplusn-team
repository:
  name: agent_workflow
  url: https://github.com/oneplusn-team/agent_workflow
boss:
  github_username: oneplusn-boss
  email: oneplusn_boss@163.com
# agents: 字段记录已上岗员工（第9步更新）
```

---

## 确定 Agent 身份

### 可选角色（8个）

| 角色 | 说明 | SOUL.md 来源 |
|------|------|-------------|
| developer | 开发工程师 | engineering-senior-developer.md |
| reviewer | 代码审查员 | engineering-code-reviewer.md |
| architect | 架构师 | engineering-software-architect.md |
| tester | 测试工程师 | testing-embedded-qa-engineer.md |
| project-manager | 项目经理 | project-management-project-shepherd.md |
| insight-specialist | 洞察专员 | strategy/nexus-strategy.md |
| research-analyst | 调研分析师 | academic/academic-literature-reviewer.md |
| security-engineer | 攻防对抗工程师 | engineering-security-engineer.md |
| custom | 自定义 | 用户提供 |

### 邮箱配置（GitHub 注册 + SMTP 自动发邮件）

每个数字员工需要两个邮箱用途：
1. **GitHub 注册邮箱** — 用于注册 GitHub 账号
2. **SMTP 发件邮箱** — 用于数字员工自动发邮件给老板（日报/通知）

推荐使用 **163 邮箱**（免费、稳定、SMTP 支持好）。

---

#### 情况一：已有邮箱（老板邮箱可用 + 别名）

如果老板已有 163 邮箱（如 `xxx@163.com`），**强烈推荐**使用 `+` 别名功能：

- 员工1邮箱：`xxx+dev01@163.com`（邮件自动转发到 `xxx@163.com`）
- 员工2邮箱：`xxx+rev01@163.com`
- 以此类推

**原理**：163 邮箱支持 `+` 别名，所有发送到 `xxx+别名@163.com` 的邮件都会自动进入 `xxx@163.com` 的收件箱，无需注册新邮箱！

---

#### 情况二：没有邮箱 — 引导创建 163 邮箱

如果老板没有 163 邮箱，需要**先为老板注册一个主邮箱**，然后员工使用 `+` 别名。

**163 邮箱注册详细步骤**：

```
步骤 1：访问官网
  - 打开浏览器，访问 https://mail.163.com
  - 点击页面右侧的【注册新账号】

步骤 2：选择注册方式
  - 选择【注册字母邮箱】（推荐）
  - 或选择【手机号注册】

步骤 3：填写注册信息
  - 邮箱地址：输入想要的用户名（如 oneplusn_team）
    → 完整邮箱为: oneplusn_team@163.com
  - 密码：设置强密码（8位以上，含大小写字母+数字）
  - 手机号：输入能接收短信的手机号

步骤 4：手机验证
  - 点击【获取验证码】
  - 输入收到的 6 位短信验证码
  - 点击【立即注册】

步骤 5：注册完成
  - 记住邮箱地址和密码
  - 建议设置安全问题（方便找回密码）
  - 建议绑定微信（方便登录和安全验证）

⚠️ 重要提醒：
  - 这个主邮箱将作为所有员工 + 别名的基础邮箱
  - 老板需要妥善保管密码
  - 后续开启 SMTP 需要用到这个邮箱
```

---

#### 步骤三：开启 SMTP 服务 + 获取授权码

**目的**：获得 SMTP 授权码，数字员工才能通过代码自动发邮件给老板。

**详细步骤**：

```
步骤 1：登录邮箱
  - 打开 https://mail.163.com
  - 用刚注册的邮箱地址和密码登录

步骤 2：进入设置
  - 点击页面右上角的【设置】按钮（齿轮图标）
  - 在下拉菜单中选择【POP3/SMTP/IMAP】

步骤 3：开启 SMTP 服务
  - 找到【POP3/SMTP服务】栏目
  - 点击右侧的【开启】按钮
  - 会弹出确认窗口，点击【继续开启】

步骤 4：短信验证
  - 系统会要求发送短信验证
  - 两种方式：
    a) 扫码发送（推荐）
    b) 点击下方【手动发送短信】，按提示发送短信到指定号码
  - 发送完成后，点击【我已发送】

步骤 5：获取授权码
  - 验证通过后，系统会生成一串 16 位授权码
  - 格式类似：lunkbrgwqxhfjgxx
  - ⚠️ 授权码只显示一次！立即复制保存！
  - ⚠️ 这不是邮箱密码，是专门给 SMTP 用的授权码

步骤 6：继续开启 IMAP（可选但推荐）
  - 找到【IMAP/SMTP服务】栏目
  - 同样点击【开启】并完成验证
  - 也会获得一个授权码（和上面的一样用）
```

**SMTP 配置参数**（数字员工自动发邮件时使用）：

```yaml
smtp:
  server: smtp.163.com
  port: 465              # SSL 加密端口
  username: xxx+dev01@163.com   # 员工邮箱（+ 别名）
  password: 授权码        # 上面获取的 16 位授权码（不是邮箱密码！）
  use_ssl: true
  sender_name: "数字员工 dev-01"
  boss_email: "老板邮箱@example.com"   # 日报发送目标
```

**⚠️ 安全提示**：
- 授权码只显示一次，建议截图保存到密码管理器
- 如果忘记授权码，可以重新进入设置 → 先关闭再重新开启服务，会生成新的授权码
- 修改邮箱密码后，授权码会失效，需要重新获取
- 建议每 90 天更新一次授权码

---

### GitHub 账号

脚本提供 5 种方式配置 GitHub 账号：

**[A] 已有账号** — 直接输入用户名/邮箱/Token

**[B] 引导创建** — 显示完整教程，按步骤注册后回来继续
- 打开 https://github.com/signup
- 输入邮箱（使用上面配置好的 + 别名邮箱，如 `xxx+dev01@163.com`）
- 设置用户名（建议: {org}-{name}，如 myteam-dev01）
- 完成邮箱验证
- 选择 Free 计划
- 老板将账号加入 Organization
- 账号接受邀请

**[C] + 别名邮箱（推荐）** — 用老板邮箱的 + 别名
- 如果老板邮箱是 `xxx@163.com`，建议用 `xxx+dev01@163.com`
- 无需注册新邮箱，邮件自动转发到原邮箱
- 用户名建议: {org}-{name}

**[D] 复用 Token** — 与老板共享（快速但不推荐）

**[Q] 跳过** — 稍后手动配置

### PAT Token

每个员工需要独立的 Fine-grained PAT Token：

创建步骤:
1. 用员工 GitHub 账号登录
2. Settings → Developer settings → Personal access tokens → Fine-grained tokens
3. Generate new token:
   - Token name: oneplusn-{name}-token
   - Expiration: 90 天或 No expiration
   - Repository access: All repositories
4. 权限勾选:
   - Contents: Read and write
   - Issues: Read and write
   - Pull requests: Read and write
   - Members: Read-only (Organization)
5. Generate → 立即复制保存（只能看一次）

---

## 创建 Hermes Profile

先判断：**新员工使用的模型是否与已有 Profile 相同？**

### 情况一：使用相同模型（clone）

如果客户使用与现有 Profile 相同的模型和 API Token，直接 clone 即可，无需重新配置模型：

```bash
hermes profile create {name} --clone
```

clone 会复用源 Profile 的模型配置和 API Token，`config.yaml` 中的 `model` 段保持不变。

### 情况二：使用不同模型（配置模型 + API Token）

如果客户使用其他模型，clone 后需要再配置该员工的模型和 API Token：

```bash
hermes profile create {name}
```

配置 `config.yaml`，按实际使用的模型填写 `provider` / `name`，并在 `.env` 中写入对应的 API Token：

```yaml
model:
  provider: openai        # 按实际填写: openai / anthropic / ...
  name: gpt-4             # 按实际填写模型名
  temperature: 0.7
  max_tokens: 4096

memory:
  type: vector
  backend: chroma
  persistence: true
```

```bash
# .env 中追加该员工的 API Token
MODEL_API_KEY={api_token}
```

⚠️ 不同模型的 `provider`、`name` 和 API Token 各不相同，需为该员工单独配置，不要复用其他模型的 Token。

---

## 绑定 GitHub

写入 `.env`：

```bash
GITHUB_USERNAME={username}
GITHUB_EMAIL={email}
GITHUB_TOKEN={token}
GATEWAY_PORT={port}
AGENT_NAME={name}
AGENT_ROLE={role}
```

---

## 注入角色灵魂

脚本自动从 [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) 匹配 SOUL.md。

流程：
1. 根据角色自动匹配对应的 `.md` 文件
2. 显示预览（角色名称、核心使命、技能清单）
3. 用户选择：
   - `y` - 直接使用
   - `n` - 搜索其他角色替换
   - `e` - 编辑修改后使用
4. 如果找不到匹配文件 → 生成通用默认值 → 用户可编辑

匹配表见 [prompts.md](prompts.md) 开头的对照表。

---

## 阅读团队 README

### 获取 README

```bash
curl -s https://raw.githubusercontent.com/{org}/{repo}/main/README.md
```

### 入职确认（3个问题）

发送给 Agent，含默认答案建议：

**Q1: 你的角色和职责是什么？**
> 默认建议："我是 [{名字}]，担任团队的 [{角色}]。主要职责包括 [{角色职责描述}]。我向老板汇报工作，与团队其他成员协作完成任务。"

**Q2: 团队的工作流程是怎样的？**
> 默认建议："团队通过 GitHub Issues 进行任务管理。流程为：老板创建 Issue → 分配给我 → 我处理并更新状态 → 完成后提交 PR → 审查通过 → 合并关闭。我每半小时轮询一次新任务。"

**Q3: 如何与其他成员协作？**
> 默认建议："我通过 GitHub Issues 的评论与其他成员沟通。当需要协作时，我会 @ 相关成员。如果遇到阻塞超过2小时，我会升级给老板。所有工作成果通过 PR 提交，经过审查后合并。"

用户可选择使用默认答案，或自行编辑修改。

---

## 启动 Gateway

```bash
hermes profile use {name}
hermes gateway start --port {port}
```

---

## 配置定时任务

每个数字员工自动创建 **3 个公用 cronjob**。

### 默认配置（展示给用户，可修改）

```yaml
  - name: task-polling
    schedule: "0,30 * * * *"
    action: "github issue scan --assignee self --auto-process"
    # 每半小时轮询一次 GitHub Issue
    # 可修改: 错峰分钟点（0,30 / 15,45 / 10,40 或自定义两个分钟点）

  - name: config-backup
    schedule: "0 20 * * *"
    action: "config backup --to hermes-config/{name} --exclude-env --commit-push"
    # 每天 20:00 备份 hermes config 到 GitHub hermes-config/{name}/
    # ⚠️ 排除 .env（含 GITHUB_TOKEN、MODEL_API_KEY），只备份 config.yaml + cron 配置
    # 可修改: 备份时间

  - name: memory-cleanup
    schedule: "0 21 * * *"
    action: "memory cleanup --archive-older-than 30d --hindsight-optimize"
    # 每天 21:00 清理记忆；装了 hindsight 则做高级记忆优化与清理
    # 可修改: 清理时间、保留天数
```

### 轮询错峰

所有员工都每半小时轮询一次，可错开分钟点避免同时打 GitHub：

| 预设 | cron | 含义 |
|------|------|------|
| `0,30` | `0,30 * * * *` | 每小时 0 分、30 分 |
| `15,45` | `15,45 * * * *` | 每小时 15 分、45 分 |
| `10,40` | `10,40 * * * *` | 每小时 10 分、40 分 |

也可自定义任意两个分钟点，写 `10/40` 或 `10,40` 均可。

### 用户可执行的操作

- 修改轮询错峰分钟点
- 修改备份/清理的时间
- 直接使用默认配置

---

## 更新 handoff.yaml

上岗完成后自动更新，追加 Agent 信息：

```yaml
agents:
  dev-01:
    name: dev-01
    role: developer
    github_username: oneplusn-dev01
    github_email: oneplusn_dev01@163.com
    gateway_port: 8081
    status: active
    onboarded_at: 2026-06-03 12:00:00
```

**作用**：
- 记录所有已上岗员工的完整信息
- 查看团队组织关系
- 避免名字/端口冲突
- 为后续添加新员工提供参考