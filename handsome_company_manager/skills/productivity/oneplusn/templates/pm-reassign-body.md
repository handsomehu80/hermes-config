# PM Reassign Body — Copy-Paste Template

Use this when PM reassigns a stalled or priority-violated Issue from one team member to another. Never just `gh issue edit --remove-assignee X --add-assignee Y` without this body — the new assignee inherits nothing.

## Template

```markdown
🔄 **PM 移交(<date>,老板 <letter> 指令)**

@<new-assignee> 本 Issue 由 <old-assignee> 移交。原因:**<conflict cite without blame>**。

### 已发现的 <old-assignee> 产出(请复用,不要重写)
- branch `<branch-name>` 在 workspaces/issue-<n>/
- N 个 commits:<list each with short SHA + 1-line summary>
- 关键文件:<file list with byte sizes>
- 已跑过 1 轮 <test>:**<verdict>**(<key numbers>)
- `<scratchpad>` 留痕(本地有 .ralph/<file>)

### 你的收尾动作
- [ ] **不要重写代码** — 基于已有 workspace 验证即可
- [ ] **核心交付物 `<output_file>`** — 整理已有 <source>,产 ≤ X 字
- [ ] **验证 <关键约束>** — grep `<file>` + system prompt(确认无 <forbidden> 工具)
- [ ] **构造 <boundary scenario>** — 临时改 `<config>` cap,确认熔断真生效
- [ ] **提 PR** — branch `<branch>` → main,PR body 用 `Closes #<n>`
- [ ] 完成所有收尾后,**本 Issue 可自 close**(only-reviewer-can-close 铁规授权)

### 不要做的事
- 不重写 <core file>(信任 <old-assignee> 已实现)
- 不重跑完整 <test>(增量验证 1-2 项即可,避免重复浪费)
- 不与 <old-assignee> 在 <related Issue> 上协调(<old-assignee> 已被 PM 催回 <priority>)

### 期望响应时间
**<N> 个 <role> cron tick(<分钟>)出 <deliverable> + PR**

— PM (@<pm-handle>)
```

## Worked Example (Issue #10 reassigned from dev → reviewer, 2026-07-14)

```markdown
🔄 **PM 移交(2026-07-13,老板 C 指令)**

@Handsome-Review 本 Issue 由 dev 移交。原因:**dev 在 #6/#7 上认领 9 小时无产出,优先级串台**。dev 在 workspace 已经跑过 1 轮 PoC 并 evaluator PASS,**你的工作是 verification + 收尾,不重写代码**。

### 已发现的 dev 产出(请复用,不要重写)
- branch `feat/issue-10-ralph-loop-poc` 在 workspaces/issue-10/
- 3 个 commits:`feat: add Ralph loop PoC harness` / `fix: populate Ralph scratchpad from issue context` / `docs: add hello smoke test usage docs`
- 关键文件:`poc/ralph-loop.sh` (14730B) / `poc/evaluator.sh` (3002B) / `poc/scratchpad-template.md`
- 已跑过 1 轮 smoke test:**evaluator 判定 PASS,7/7 单测过,Claude CLI 报告费用 $0.491**(见 workspaces/issue-10/.ralph/comment-issue-12.md 草稿)
- `hello_test.sh` 实跑 exit=0(PM 已自测)

### 你的收尾动作
- [ ] **不要重写代码** — 基于 dev 已有的 workspace 验证即可
- [ ] **核心交付物 `docs/loop-poc-results.md`** — 整理 dev 的 .ralph/ 留痕 + commit + 实跑数据(至少含:收敛 iterations / 实际 USD 消耗 / evaluator 命中率 / 跑通耗时 4 项)
- [ ] **验证 evaluator 真无 Write/Edit 工具** — grep `poc/evaluator.sh` + system prompt
- [ ] **构造 budget 超限场景** — 临时改 $0.01 cap,确认熔断真生效 + Issue 评论 `>verifier-budget-exceeded` 真写出来
- [ ] **提 PR** — branch `feat/issue-10-ralph-loop-poc` → main,**PR body 用 `Closes #10`**
- [ ] 完成所有收尾后,**本 Issue 可自 close**(only-reviewer-can-close 铁规授权)

### 不要做的事
- 不重写 ralph-loop.sh(信任 dev 已实现)
- 不重跑完整 PoC(增量验证 1-2 项即可,避免重复浪费)
- 不与 dev 在 #6/#7 上协调(dev 已被 PM 催回 P0)

### 期望响应时间
**1-2 个 reviewer cron tick(20-40 min)出 docs/loop-poc-results.md + PR**

— PM (@Handsome-Manager)
```

## Why These Sections Matter

| Section | What it prevents |
|---|---|
| **已发现的 X 产出(请复用,不要重写)** | new assignee throwing away dev's work to start over (burns hours + tokens) |
| **关键文件** | new assignee re-deriving branch name / workspace path / commit SHA |
| **已跑过 1 轮 <test>** | new assignee running the full test suite again instead of incremental verification |
| **你的收尾动作 (checkbox)** | new assignee picking arbitrary scope, not the narrow "verify + wrap" needed |
| **不要做的事** | new assignee chasing tangents or re-coordinating with the original assignee |
| **期望响应时间** | new assignee treating a P0 wrap-up like a multi-day research project |

## Anti-patterns

- ❌ **Reassign without this body** — the new assignee starts from zero and redoes everything.
- ❌ **Blame framing** ("dev failed to deliver, you're picking up the pieces") — burns trust; the team member you reassign to will quietly resent the framing. Use "已发现的 dev 产出 + 请复用" instead.
- ❌ **Missing "不要重写 X"** — almost always triggers a rewrite. Be explicit.
- ❌ **"Take your time" / no cadence** — wrap-ups can drag for days if unbounded. Always cite cron-tick budget.
- ❌ **Forgetting to `gh issue edit --remove-assignee X --add-assignee Y` first** — the body references the new assignee but the assignee field still points to the old one. Issue ownership looks ambiguous in the dashboard.

## Tool: Atomic Reassign Command

```bash
gh issue edit <n> --repo <org>/<repo> \
  --add-assignee <new> \
  --remove-assignee <old>
```

Run this BEFORE posting the body. The comment then references the assignee state that matches the actual label.