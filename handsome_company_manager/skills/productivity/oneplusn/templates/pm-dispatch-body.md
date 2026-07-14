# PM Dispatch Body — Copy-Paste Template

Use this when PM creates a GitHub Issue to assign work to a 1+N employee (developer / reviewer / architect / etc).

## Template

```markdown
## 背景
[One-paragraph trigger: "老板要求 / PM 综合稿结论 / 上游 blocker" + link to source]

## 必读(<if there are references>)
- [path/to/ref.md] — <one-line summary>
- [<url>] — <one-line summary>

## 你的任务

### 阶段 1:<if design needs confirmation>(本 Issue 评论里,本 cron tick 完成)
- [ ] <position on design point 1>
- [ ] <position on design point 2>

### 阶段 2:实施 / 验证(下个 cron tick 起,预计 <N> tick)
- [ ] 写 `<path>`(<one-line summary>)
- [ ] 写 `<test>`(<one-line summary>)
- [ ] 跑通 <test>,产出 4 数据点
- [ ] 文档 `<docs>`(含 mermaid / 架构图)

### 阶段 3:PR
- [ ] 提 PR 关联本 Issue,`Closes #<n>`,body 含 <deliverable> 摘要

## 反脆弱护栏(不可违反)
- ❌ <rule 1>
- ❌ <rule 2>
- ❌ <rule 3>

## 6 铁规提示
- 单 assignee = <role>
- 完成 PR 后由 reviewer 验,reviewer 才能 close
- 评论中文
- **本 Issue 是 P<n>**,优先于未结的 P<m>(m < n)
- 每 1 个 cron tick 在本 Issue 评论更新进度

## 期望响应时间
- **本 cron tick 内**完成 §<section> 评论(否则视为优先级再次串台)
- <N> tick 内出 PR
```

## Key Rules

1. **Always include "期望响应时间"** — without it, P0 gets treated like P2
2. **Cross-reference related Issues with #<n> not "the other one"** — survives repo growth
3. **Single assignee per 铁规** — never assign to multiple people; if reviewer also needs to see it, mention them in comment with @ not in assignee field
4. **Cadence line + P-level together** — "本 cron tick 内完成 §X 评论" + "本 Issue 是 P<n>"
5. **Acceptance criteria are observable** — "writes `budget_middleware.py` with ≥5 unit tests" not "implement budget middleware well"

## Variant: When Dev's Priority Was Violated

If this is a P0 escalation against dev who previously let P1 sit for 9+ hours, add a hard line:

```markdown
⚠️ **历史**:你本 Issue 之前在 <original-priority> 认领 <X> 小时无 commit / 无 PR / 无后续评论。**P0 必须每 1 个 cron tick 在本 Issue 评论更新进度**(哪怕只是 "in progress, 本 tick 完成 X")。再次沉默 = 该 Issue 升级为 status:blocked 并找老板协调。
```

This sounds firm but is calibrated to the actual failure mode (沉默) and the actual consequence (升级 + 老板), not blame.

## Anti-patterns

- ❌ **Long background paragraphs** — dev / reviewer will skim. First 3 lines must convey what + why.
- ❌ **No cadence** — leads to P0 treated as P2.
- ❌ **No 反脆弱护栏** — leads to dev introducing forbidden patterns (e.g., extra sub-agents, banned tools).
- ❌ **Cross-references like "see issue" without #** — won't survive repo search.
- ❌ **Multiple assignees** — violates 6 铁规; mention additional people in body via @ instead.