# Loop Engineering 团队演进路线图

> **来源**:2026-07-13 PM 综合洞察(3 份调研报告 + 9 个一手 fetch 的 URL)
> **本地路径**:C:\Users\Administrator\loop-engineering-upgrade-playbook.md
> **审计**:C:\Users\Administrator\loop_engineering_research_report.md (dev 视角) + loop-engineering-critical-review.md (reviewer 视角) + loop-engineering-upgrade-playbook.md (PM 综合) + docs/insight-feasibility-scorecard.md (reviewer 审计)
> **状态**:#9 reviewer audit 已 close; #6 #7 #10 #11 in-flight; final synthesis 等所有 close 后由 PM 综合

## 一句话

Loop Engineering = Harness 之上的**控制平面**(触发器 + 状态外化 + verifier + 熔断)。我们 1+N 已有粗粒度 long-cycle loop,真正的升级不是"上 loop",而是**单 tick 内补 verifier + budget + tool 授权边界**。

## 四层范式坐标(2022→2026)

| 层 | 时间 | 核心问题 | 代表 |
|---|---|---|---|
| Prompt Engineering | 2022–2024 | 怎么说得对 | CoT, Few-shot |
| Context Engineering | 2025 | 给什么上下文 | Lütke, Karpathy, Anthropic 2025-09 |
| Harness Engineering | 2025 末–2026 Q1 | 执行环境怎么稳 | OpenAI Codex 1M 行零人工、Anthropic 3 篇 harness 论文 |
| **Loop Engineering** | 2026 年 6 月 | 谁找活/谁做/谁查/明天怎么接今天 | Steinberger 7 Jun, Addy Osmani 8 Jun, Boris Cherny "I don't prompt Claude anymore" |

## 三个流派(我们选 B)

| 流派 | 代表 | 我们 1+N 适配度 |
|---|---|---|
| A. 纯 bash Ralph | Huntley 原版, `while :; do cat PROMPT.md \| claude ; done` | ⚠️ 外壳可借 |
| **B. State machine + verifier** | **Anthropic 200 features JSON, cwc-long-running-agents, GAN planner/generator/evaluator** | ✅ **高 — reviewer 当 evaluator, Issue 当 JSON state, 零新基建** |
| C. Multi-agent factory | Gas Town (Yegge), multiclaude, Brownian Ratchet | ❌ 极低 — 3 人用是 over-engineering |

**Sutton bitter lesson**:`Gas Town is just a series of Ralph loops with extra steps`. 简单 + 算力 > 编码人类知识的专用方法。

## 5 阶段升级剧本(我们停在 Stage 3)

| Stage | 目标 | 我们当前 | 动作 |
|---|---|---|---|
| **0. Inventory** | 盘点 harness 5 层 + tick 内盲区 | 部分 | 写 harness-inventory.md, 1 周 |
| **1. Manual loop** | 人在 loop 上, agent 一次性 | ✅ 现状 | 沉淀最佳实践 |
| **2. Auto loop + verifier + budget** | per-tick USD cap + scratchpad + evaluator | 🟡 Issue #6 #7 进行中 | 1 周内 Stage 2 完整闭环 |
| **3. State-externalized + sub-agent 仲裁** | Issue 结构化字段 + reviewer sub-agent + 单实例 verifier | ⚠️ 6 铁规仍是 README RULES, 未编入 gateway hook | 3-5 周 |
| **4. Coordinated multi-loop** | worktree + 跨 loop conflict watcher | ❌ 无 | **不启用** — 3 人用边际收益为负 |

**当前适配度 6.5/10, 目标 Stage 3 顶端 = 8.5/10**。

## 1-3-5 PM 行动清单

### 1 周内(Stage 0)
- 写 `harness-inventory.md`, 5 层逐项 ✅/⚠️/❌
- 列 3 个 ❌:无 budget 熔断 / 无 tick 内 verifier / 无 tool 授权边界
- 跑通 1 条代表性 Issue 的手工端到端流程

### 3 周内(Stage 2 — 分水岭)
- per-tick USD cap gateway($5/$20)
- scratchpad 模板 `.ralph/scratchpad-<issue>.md`
- evaluator sub-agent(无 Write/Edit 工具)
- 6 铁规新增 #7 per-tick spend cap
- 3 条低风险 L1 Issue 无人值守试点(纯文档 / 纯 lint / 纯测试补全)

### 5 周内(Stage 3)
- Issue 模板 v2(`## Goals / ## Pass Criteria / ## Files`)
- reviewer sub-agent 灰度
- verifier 全局单实例
- go/no-go: 自动评审捕获率 ≥ 30%

## 3 个停止信号

1. **边际信号**: 加新抽象但单 Issue 解决时间未下降 ≥ 30%
2. **认知信号**: PM 不能一句话解释新组件
3. **失败信号**: Stage 2 budget 熔断连续 4 周没被触发

## 4 个反脆弱护栏(不能踩)

| 坑 | 护栏 |
|---|---|
| evaluator sub-agent 给 Write 工具 | 模板化强制 tool=none |
| verifier 并行 fan-out | Huntley 原话"only 1 for build/test/validation" |
| 上 multi-agent factory | 3 人用 Gas Town 用反了方向 |
| 6 铁规当 policy 不当 tooling | Stage 2 必须编进 hook |

## 决策表(不要重新发明)

| 决策 | 决定 | 论据 |
|---|---|---|
| 自研 loop 框架? | **不** | Anthropic cwc-long-running-agents 已开源 |
| 流派? | **Hybrid: Ralph 外壳 + Anthropic JSON state + reviewer verifier** | 流派 B 几乎零新基建 |
| 第一个无人值守试点? | **文档/lint/测试补全** | 天然 verifier, 失败代价极低 |
| Stage 4 启用条件? | **团队到 10 人再考虑** | 3 人协调开销边际收益为负 |
| 模型选择? | **不换模型,改 harness** | OpenAI 5 个月实验 = 3.5 PR/人/天, 不换模型 |

## 一手参考 URL(均 fetch 验证)

1. https://openai.com/index/harness-engineering — OpenAI Codex "effectively this is a Ralph Wiggum Loop" 原话
2. https://chrismdp.com/your-agent-orchestrator-is-too-clever — Sutton bitter lesson + Gas Town 是 "Ralph + extra steps"
3. https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town — Gas Town 内部机制
4. https://ghuntley.com/ralph — Huntley 原版 bash loop + "deterministically bad"
5. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents — 200 features JSON + Opus 4.5 也 one-shot 失败
6. https://www.anthropic.com/engineering/harness-design-long-running-apps — GAN 风格 planner/generator/evaluator
7. https://martinfowler.com/articles/harness-engineering.html — ThoughtWorks 框架
8. https://developers.redhat.com/articles/2026/04/07/harness-engineering-structured-workflows-ai-assisted-development — Red Hat 实现指南
9. https://www.truefoundry.com/blog/aiewf-2026-loops-harness-engineering — AIEWF 2026 三段弧 + 27.6%/48% verification crisis
10. https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026 — Loop Engineering 完整定义
11. https://github.com/anthropics/cwc-long-running-agents — Anthropic 模板(含 evaluator sub-agent)

## 实时进展(更新日期 2026-07-13)

| # | 派给 | 标题 | 状态 |
|---|---|---|---|
| #6 | dev | per-tick USD 熔断网关 | 🟡 in-progress |
| #7 | dev | scratchpad + evaluator | 🟡 in-progress |
| #8 | reviewer | P1 双改造 E2E 验证 + 6 铁规第 #7 | ⏸ 等 #6/#7 |
| #10 | dev | 最小 Ralph loop PoC | 🟢 已接 + workspace 已 commit |
| #11 | reviewer | 验 PoC + 最终 insight 综合稿 | ⏸ 等 #10 |
| #9 | reviewer | 审计 3 份调研报告 | ✅ DONE |