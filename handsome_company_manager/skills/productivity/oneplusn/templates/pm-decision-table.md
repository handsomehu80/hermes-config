# PM 拍板 Decision Table — Copy-Paste Template

Use this at the top of any design doc that required a dev/reviewer disagreement resolution. PM synthesizes — does not delegate up.

## Header (insert above §1 of the design doc)

```markdown
# <project-name> Design Discussion Draft

> **作者:** PM (@Handsome-Manager)
> **v1 日期:** <date> (原始草案)
> **v2 日期:** <date> (PM 拍板,综合 dev @ #<n> + reviewer @ #<n> 反馈)
> **状态:** v2 已成 PM 拍板稿,dev 在 #<n> 立即按 v2 实施,reviewer 在 #<n+1> 等 #<n> close 后开始验证
> **目的:** <one-line trigger>

---

## 🔴 PM 拍板(<date>,老板选 <A|B|C>:<synthesis|standalone>)

> 综合 #<n> dev @<dev-handle> 与 #<n+1> reviewer @<reviewer-handle> 的设计讨论,以下决策已拍板,任何后续变更需 PM 重审。

| 决策点 | **拍板结果** | 采纳方 | 论据 |
|---|---|---|---|
| <point 1> | **<result>** | <dev|reviewer|both> | <one-line why> |
| <point 2> | **<result>** | <...> | <...> |
| <point 3> | **<result>** | <...> | <...> |
| ... | ... | ... | ... |

**dev 在 #<n> 的下个 cron tick 必做**:
1. 把 DESIGN.md §<which> 全部按本表更新
2. 起 `<dir>/` 骨架
3. 实现 <core files>
4. 跑通 loop,产出 <deliverable>
5. 提 PR `Closes #<n>`

**reviewer 在 #<n+1> 等 #<n> close 后必做**:
1. 验证 <key constraints>
2. <verifier action>
3. 写 `<report>` 给老板

---
```

## Issue Comment Template (post after committing v2)

```markdown
🔴 **PM 拍板通知(<date>,老板选 <letter>:综合最佳)**

@<assignee> 你和 @<other-assignee> 在 §<n> 的设计讨论已读。**老板拍板综合方案**,以下决策立即生效:

| 决策 | 拍板结果 |
|---|---|
| ... | ... |

<for each adopted-side, briefly note the deviation from their proposal and why>

DESIGN.md v2 已 commit 在本地(`<short-sha>`),**git push 暂时网络问题**(详见进展报告)。下个 <role> cron tick 必做:

1. ...
2. ...
3. ...

请在本 Issue 评论里确认收到拍板 + 报下一步动作。

— PM (@<pm-handle>)
```

## Worked Example (from Snake game 2026-07-14)

See `oneplusn` skill `references/pm-operations-playbook.md` §6 for the full worked example. Key shape:

```markdown
| 决策点 | 拍板结果 | 采纳方 | 论据 |
|---|---|---|---|
| ralph-loop 语言 | **Python**(`ralph_loop.py`)+ 5 行 bash 包装 | dev | Windows `jq` 缺失 + 路径 + 子进程 env 都更稳 |
| features.json schema | **加 `depends_on`** 不加 `priority` + 补 **`pass_criteria`** + **`attempts[]`** | dev + reviewer | 依赖客观,priority 主观;attempts 给审计真源 |
| features 数量 | **保留 8 项**(不合并) | reviewer | 验收契约必须独立;合并 wall/self 会丢独立 fail 信号 |
| L2 verifier fuzzing | **Seeded property test**(20 seed × 50 输入),不用裸 `Math.random()` | reviewer | 可复现失败 + 防硬编码更可靠 |
| `max_iterations` | **16**(总)+ **`max_attempts_per_feature = 3`** | reviewer | 8 features × 1 失败 = 后 5 个没机会;16 留 2× 重做空间 |
| `$20` escalation | **不是自动续跑**,仅 PM/老板批准后累计上限 | reviewer | 防 burst budget |
| 反脆弱护栏 | builder deny `features.json` + evaluator deny `Write/Edit/Bash` + orchestrator 独占写 `passes` + commit 绑 feature_id+verdict+state_hash | reviewer | 双层防线 |
```

## Why This Works

1. **Boss reads top-down, picks A/B/C by letter** — matches existing preference (memory)
2. **Dev implements against v2, not v1 + scattered comments** — saves 1-2 design rounds
3. **Reviewer verifies "拍板 was followed"** by scanning the table, not the discussion history
4. **Future sessions get a single source of truth** — the table at top + design rationale below

## Anti-patterns

- ❌ **Long prose rationales** — boss won't read them. Use table rows.
- ❌ **PM saying "let boss decide"** — that's abdication, not synthesis. Boss wants PM to make a defensible call.
- ❌ **Synthesizing when one side is factually wrong** — correct the error, don't compromise.
- ❌ **Skipping the论据 column** — without论据, future PM sessions can't see why the call was made.
- ❌ **No commit hash in the comment** — the commit is the audit trail. Always include.