# PM Operations Playbook — Day-to-Day 1+N Team Management

Companion to `oneplusn` skill § "PM Operations". This file collects the worked patterns and pitfalls from real sessions — the kind of detail that doesn't belong in SKILL.md's main flow but is essential when PM gets called on to manage the team mid-flight.

## §1 — Dispatch Body Template

When PM creates a GitHub Issue to assign work to a team member, the body must answer five questions within 30 seconds of read:

1. **What** — single-sentence scope (not a paragraph)
2. **Why** — link to the trigger (boss request / synthesis report / blocking issue)
3. **Acceptance** — checkbox list, observable, specific
4. **Constraints** — what NOT to do, explicit 6-iron-rule reminders
5. **Cadence** — expected response time per cron tick (e.g., "claim in 1 tick, deliver in 3–5")

```markdown
## 背景
[One-paragraph trigger: "老板要求 / PM 综合稿结论 / 上游 blocker"]

## 目标
[One-sentence "完成 X 后,即可 Y"]

## 验收标准
- [ ] Observable outcome 1
- [ ] Observable outcome 2
- [ ] ...

## 反脆弱护栏(不可违反)
- ❌ Don't break rule 1
- ❌ Don't break rule 2
- ❌ Don't introduce dependency X

## 6 铁规提示
- 单 assignee = <role>
- 完成 PR 后由 reviewer 验,reviewer 才能 close
- 评论中文
- **本 Issue 是 P<N>**,优先于未结的 P<M>(M < N)
- 每 1 个 cron tick 在本 Issue 评论更新进度

## 期望响应时间
- **本 cron tick 内**完成 §X 评论(否则视为优先级再次串台)
- N tick 内出 PR
```

The cadence line is the single most-skipped field. Without it, the team treats P0 like P2. Add it explicitly.

## §2 — Quality Audit Workflow

When boss asks "is anyone slacking?" or "项目进展怎么样了", do NOT just `gh issue list`. Walk the four-layer ladder:

### Layer 1: Issue state surface

```bash
gh issue list --state all --limit 20 --json number,title,state,assignee,labels
gh pr list --state all --limit 20 --json number,title,state,additions,author
```

This is the "what does the dashboard say" pass. **Insufficient on its own** — Issue state is self-reported by team members and can be stale by hours.

### Layer 2: Per-Issue audit (for each open + recently-closed Issue)

```bash
# Full comment thread for one Issue
gh api /repos/<org>/<repo>/issues/<n>/comments --jq '.[] | {at: .created_at, who: .user.login, body: .body}'
# Latest 5 comments, summarized
gh api /repos/<org>/<repo>/issues/<n>/comments --jq 'sort_by(.created_at) | reverse | .[0:5] | .[] | "\(.created_at) \(.user.login): \(.body[0:80])"'
```

Look for:
- "Claimed at T, no comment since T+9hr" → **flag, this is the摸鱼 signature**
- "Issue closed but related PR still OPEN" → flag, see Pitfall #1 in SKILL.md
- "Comment thread is just `[ack]`-style — no technical progress" → softer red flag

### Layer 3: PR diff audit (spot-check 1 PR minimum)

```bash
gh pr view <n> --json files,title,additions,deletions | jq '{title, files: [.files[] | {path, add: .additions, del: .deletions}]}'
gh pr diff <n> | head -200
```

For deeper inspection, fetch the file locally:

```bash
git fetch origin pull/<n>/head:pr-<n>
git checkout pr-<n> -- <specific_file>
cat <specific_file> | head -100
```

**Do not trust "+901 lines" as evidence of quality.** Read 50 lines and judge.

### Layer 4: Workspace / branch inspection

```bash
# Find dev's per-Issue workspaces
ls /d/<work-dir>/workspaces/
# Inside a workspace, check git log
cd /d/<work-dir>/workspaces/issue-<n> && git log --oneline
# Untracked files = work-in-progress that hasn't been committed
git status --short
```

The `?? .ralph/` pattern (untracked scratchpad dir) is the giveaway that dev is iterating on Ralph-loop scaffolding without committing. Not摸鱼 per se, but **communication gap** — work is happening but not visible.

## §3 — Reassign-with-Context Body Template

When PM reassigns a dev's stalled work to reviewer (or vice versa), the body must answer:

1. **Why** — without blame. Cite the conflict ("P1 unblocked by P0 escalation", "dev's other deliverables pending"), not the person.
2. **Existing artifacts to reuse** — branch, commits, workspace files. With paths. Reviewer must not have to re-derive.
3. **What NOT to do** — explicitly forbid rewrite, recompute, restest from scratch.
4. **What TO do** — narrow: "verify the 4 data points in `loop-poc-results.md`", not "redo the PoC".
5. **Time budget** — explicit cron-tick expectation.

```markdown
🔄 **PM 移交(<日期>,老板 C 指令)**

@<new_assignee> 本 Issue 由 <old_assignee> 移交。原因:**<conflict cite>**。

### 已发现的 dev 产出(请复用,不要重写)
- branch `<branch-name>` 在 workspaces/issue-<n>/
- N 个 commits:<commit list with SHA + 1-line summary>
- 关键文件:<file list with byte sizes>
- 已跑过 1 轮 <test>:**<verdict>**(<key numbers>)

### 你的收尾动作
- [ ] **不要重写代码** — 基于已有 workspace 验证即可
- [ ] **核心交付物 <output_file>** — 整理已有 <source>,产 ≤ X 字
- [ ] **验证 <关键约束>** — grep `<file>` + system prompt
- [ ] **构造 <boundary scenario>** — 临时改 `<config>` cap,确认熔断真生效
- [ ] **提 PR** — branch `<branch>` → main,PR body 用 `Closes #<n>`
- [ ] 完成所有收尾后,**本 Issue 可自 close**(only-reviewer-can-close 铁规授权)

### 不要做的事
- 不重写 <core file>(信任 <author> 已实现)
- 不重跑完整 <test>(增量验证 1-2 项即可,避免重复浪费)
- 不与 <author> 在 <related Issue> 上协调(<author> 已被 PM 催回 <priority>)

期望响应时间:**<N> 个 <role> cron tick(<分钟>)出 <deliverable> + PR**

— PM (@<pm-handle>)
```

The "不要重写 X" line is non-negotiable. Without it, the new assignee often redoes work, burns tokens, and the original artifact (with all its commit history and reuse value) gets abandoned.

## §4 — PM 拍板 (Decision Synthesis) Pattern

When dev and reviewer disagree on a design choice, the PM does NOT pass the question up the chain. The PM synthesizes a v2 that:

1. **Lives at the top of the design doc**, before any technical detail — so any future reader sees the decisions first
2. **Tables the conflicts** — `| 决策点 | 拍板结果 | 采纳方 | 论据 |`
3. **Names which side's position wins and why** — even if both sides had good points
4. **Versions the doc explicitly** — `v1: 2026-07-13 (draft) | v2: 2026-07-14 (PM 拍板,综合 dev+reviewer)`
5. **Commits the v2 to git** — even if the local repo has no push yet, the commit hash is the audit trail

Then on the dispatch Issue:

```markdown
🔴 **PM 拍板通知(<date>,老板选 <letter>:综合最佳)**

@<assignee> 你和 @<other_assignee> 在 §<n> 的设计讨论已读。**老板拍板综合方案**,以下决策立即生效:

| 决策 | 拍板结果 |
|---|---|
| ... | ... |

DESIGN.md v2 已 commit 在本地(`<hash>`),**git push 暂时网络问题**(详见进展报告)。下个 <role> cron tick 必做:

1. ...
```

### Why the table format works

- Boss reads top-down, picks A/B/C by letter → matches boss's existing preference (memory: "sketch options as a small comparison table")
- Dev can implement against v2 without re-reading every comment thread
- Reviewer can verify "拍板 was followed" by scanning the table, not the discussion history
- Future sessions get a single source of truth: the table at top + the design rationale below

### When NOT to synthesize

- Both sides are equally strong and the trade-off is genuinely context-dependent → escalate to boss with A/B/C
- One side is objectively wrong (a fact-checkable error) → PM unilaterally corrects, doesn't synthesize
- The cost of synthesizing wrong exceeds the cost of waiting → escalate to boss

## §5 — Network Resilience: Git Push vs GH API

GitHub connectivity on Windows host machines can degrade in interesting ways:

- `curl https://github.com` works (returns 200) → DNS + TLS path OK
- `gh api /user` works → API path OK
- `git push` fails with "Failed to connect to github.com port 443 after 21s" → git's HTTPS stack hit a timeout the others didn't

When this happens, the team can still receive PM guidance:

1. **Post the comments first** via `gh issue comment` (uses REST API, fast)
2. **Commit locally** with `git commit -m ...` (no network needed)
3. **Try push periodically** with `git push` — when network returns, push
4. **When push finally works**, expect divergence if team also pushed: `git pull --rebase` first, then `git push`. The rebase resolves "your local commits vs theirs" cleanly if there are no conflicts.

The boss comment about "team can see拍板通知 even if DESIGN.md not pushed" is acceptable when the situation is short-lived (minutes to an hour). For longer outages, escalate to boss with options.

## §6 — Worked Example: Snake Game Loop Engineering (2026-07-14)

This is the canonical example of §4 in action:

**Trigger**: Boss said "我想实践使用 loop engineer 完成贪吃蛇游戏开发,你作为 pm 带领团队讨论怎么构建 loop"

**Flow**:
1. PM wrote `poc-snake/DESIGN.md` v1 (153 lines, 5 决策, 8 features, 3-layer verifier)
2. PM派单 to dev (#16) and reviewer (#17) for §7 design feedback
3. Dev responded with 4-point立场: Python + depends_on + 6 features (merge wall/self, game_over/restart) + 100× Math.random()
4. Reviewer responded with 4-point反方: 8 features保留 + seeded property test + 16/3 max + $20 PM-gated
5. Boss chose "C: PM 综合最佳" — PM synthesized v2 with explicit decision table:

   | 决策点 | 拍板结果 | 采纳方 |
   |---|---|---|
   | ralph-loop 语言 | Python + 5 行 bash 包装 | dev |
   | features.json schema | depends_on + pass_criteria + attempts[] | dev + reviewer |
   | features 数量 | 保留 8 项 | reviewer |
   | L2 verifier | seeded property test | reviewer |
   | max_iterations | 16 + per-feature 3 | reviewer |
   | $20 escalation | 仅 PM/老板批准 | reviewer |
   | 反脆弱护栏 | deny features.json + deny Write/Edit/Bash + commit 绑 | reviewer |

6. PM posted 拍板 comment on #16 + #17, committed DESIGN.md v2 locally, pushed after `pull --rebase` resolved divergence

**Outcome**: Both dev and reviewer had a single v2 to implement/verify against, no further clarification needed. The synthesis saved 1-2 design-rounds of back-and-forth.

## §7 — When Boss Says "再查查有没有摸鱼"

Default reflex: assume the team is working unless proven otherwise. The boss is testing the audit process, not pre-judging guilt.

**Do not**:
- Open every PR diff from scratch — pick 1 representative sample
- Run `git log` on every workspace — pick 1 workspace per assignee
- Re-read every comment thread — pick Issue with highest activity in last 24h

**Do**:
- Run Layer 1 (Issue + PR list) to map the territory
- Spot-audit 1-2 high-risk Items (assigned long ago + still in-progress)
- Check the comment-author pattern: if boss's account appears as "commenter", the cron isn't actually polling under employee identity → that's a real bug worth reporting
- Report findings as a table: `Issue | Assignee | Last Comment | Last Commit | Risk Level | Action`

Boss appreciates the structured table more than a free-text diagnosis.