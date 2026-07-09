# /oneplusn:sync — 同步 README 到 GitHub

<task>
根据 handoff.yaml 中的最新团队信息，重新生成 README.md 并提交到 GitHub 仓库。
</task>

<context>
## 使用场景

- 添加/删除员工后更新 README
- 修改团队配置后同步
- 定期维护

## 参数

`$ARGUMENTS` — 可选，`--work-dir <目录> --no-push`

- `--no-push`：只生成本地 README.md，不推送到 GitHub
</context>

<instructions>
## 步骤 1：读取 handoff.yaml

定位并读取工作目录下的 `handoff.yaml`。

## 步骤 2：生成 README.md

使用 readme-template.md 模板生成完整 README，包含以下内容：

### 2.1 头部
```markdown
# {org-name} — 协作协议

> Assignee = 轮到谁。Comment = 沟通。Close = 完成。
```

### 2.2 Mermaid 协作全景图
```mermaid
flowchart TB
    BOSS[老板 {boss_username}<br/>创建 Issue]
    TRIAGE{{有 assignee?}}
    PM[项目经理<br/>分析 → 设置 assignee]
    DEV[开发工程师<br/>开发/实施]
    REV[审查员<br/>审查/验证]
    REVIEW{{审查通过?}}
    WAIT[assignee → 老板<br/>等待终审]
    FIX[assignee → 开发<br/>修复]
    CLOSE[审查员关闭 + 通知]

    BOSS --> TRIAGE
    TRIAGE -->|无| PM
    TRIAGE -->|有| DEV
    PM --> DEV
    PM --> REV
    DEV -->|完成| REV
    REV --> REVIEW
    REVIEW -->|通过| WAIT
    REVIEW -->|打回| FIX
    FIX --> DEV
    WAIT -->|老板审批| CLOSE
```

### 2.3 团队表格
```markdown
| 名字 | GitHub | 邮箱 | 角色 | Agent类型 | 状态 |
|------|--------|------|------|----------|------|
| dev-01 | @myteam-dev-01 | ... | developer | hermes | active |
| ... | ... | ... | ... | ... | ... |
```

### 2.4 核心规则（从 rules.md 提取）

### 2.5 标签说明

### 2.6 Cronjob 配置

### 2.7 底部信息
```markdown
---
*组织: {org-name} | 仓库: {repo-name} | 更新于: {date}*
```

## 步骤 3：保存并提交

将 README.md 写入工作目录。

如果没有 `--no-push`：
```bash
cd {work-dir}
git add README.md
git commit -m "更新团队 README ({date})"
git push origin main
```

## 输出

```
[✓] README.md 已生成: {work-dir}/README.md
[✓] 已提交到 GitHub: {org-name}/{repo-name}

README 包含：
  - 协作全景 Mermaid 图
  - 团队表格 ({N} 个员工)
  - 核心规则
  - 标签说明
  - Cronjob 配置
```
</instructions>

<output_format>
- 成功用 `[✓]`，错误用 `[✗]`
- 列出 README 包含的内容清单
</output_format>
