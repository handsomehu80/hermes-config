# {{TEAM_NAME}} - 团队协作协议

> 本文档定义了 1+N 数字员工团队的工作流程和协作规范。
> 所有成员必须在协作前阅读并遵循本文档。

## 团队架构

### 老板（Owner）

| 角色 | GitHub 账号 | 邮箱 |
|------|-----------|------|
| 老板 | {{BOSS_USERNAME}} | {{BOSS_EMAIL}} |

### 组织信息

- **GitHub 组织**: https://github.com/{{ORG_NAME}}
- **主仓库**: https://github.com/{{ORG_NAME}}/{{REPO_NAME}}
- **Issue 跟踪**: https://github.com/{{ORG_NAME}}/{{REPO_NAME}}/issues

<!-- 数字员工信息将在后续阶段补充 -->

## 工作流程

### 任务生命周期

```
[创建] → [分配] → [开发] → [审查] → [测试] → [合并] → [关闭]
  ↑                                    ↓
  └──────── [阻塞/回退] ←──────────────┘
```

### 任务创建与分配

- 老板通过 GitHub Issue 创建任务
- Issue 标题格式：`[类型] 简要描述`
  - 类型: `feat`(功能) / `fix`(修复) / `docs`(文档) / `refactor`(重构) / `arch`(架构)
- 在 Issue 描述中标注：
  - 任务背景和目标
  - 验收标准（Checklist 格式）
  - 优先级标签: `P1-紧急` / `P2-重要` / `P3-一般`

### 状态标签

| 标签 | 含义 |
|------|------|
| `status:todo` | 待处理 |
| `status:in-progress` | 进行中 |
| `status:review` | 审查中 |
| `status:done` | 已完成 |
| `status:blocked` | 被阻塞 |
| `priority:P1` | 紧急 |
| `priority:P2` | 重要 |
| `priority:P3` | 一般 |

---

*本文档版本: v1.0 | 组织: {{ORG_NAME}} | 仓库: {{REPO_NAME}}*