Host: Windows 10. User home: C:\Users\Administrator. Shell is git-bash/MSYS (POSIX), NOT PowerShell — use bash syntax (ls, $HOME, &&, |, single quotes, MSYS-style /c/Users/... paths). Python: 3.11.9. Package manager: uv available, pip → python3.11. python3 command is MISSING — always invoke `python` not `python3`.
§
Hermes Agent v0.15.1, config v26, install at C:\Users\Administrator\AppData\Local\hermes\hermes-agent. Active profile: default. Single model configured: MiniMax-M3 via minimax-cn provider (https://api.minimaxi.com/v1). Agent max_turns: 150, terminal timeout: 180s, compression threshold 50% → 20%.
§
1+N 数字员工集成(2026-07-08):fork 到 Hermes。Skill `~/AppData/Local/hermes/skills/productivity/oneplusn/`,9 个 bash 命令在 `~/AppData/Local/hermes/bin/oneplusn*`(cp 副本,Windows ln-sf 坏),cron 30 分钟 + reaper 1 小时(hermes cron --no-agent)。Eval 10/10 PASS。配套 skill `claude-package-to-hermes-skill` 在 `devops/`,记 .claude 包移植方法论 + Windows 路径陷阱 + bash 包装 + cron + evals 模板。
§
Configured API keys: only MINIMAX_CN_API_KEY. Missing: OpenRouter, OpenAI, Google, xAI, Exa, Tavily, Firecrawl, Anthropic, GitHub, FAL, ElevenLabs. OAuth providers all unconfigured (Nous/Codex/xAI/Gemini). No GITHUB_TOKEN → 60 req/hr rate limit.
§
Toolset state (updated 2026-06-03): web (Tavily) ✓ enabled, browser (agent-browser + Playwright Chromium) ✓ enabled, browser-cdp still ⚠, image_gen/video_gen ⚠ (need FAL_KEY), x_search ⚠ (need XAI key), moa ⚠ (need OPENROUTER key), computer_use enabled but macOS-only (won't work on this Windows host). All other toolset gaps are by design — require their own platform credentials.
§
4-profile Agent Team (pm/eng/qa/ast) at ~/AppData/Local/hermes/profiles/ — Kanban dispatcher embedded in gateway (kanban.dispatch_in_gateway=true), 60s tick. End-to-end validated 2026-06-03: mdlinkcheck CLI build (37min, 54/54 tests, 99% coverage). Manual at ~/AppData/Local/hermes/USAGE.md. Pitfall: eng uses kanban_block(review-required) which traps parent-linked QA tasks — PM must unblock manually or fix SOUL.md.
§
用户口头报告状态 ≠ 实际状态:用户说"我的gh已经登录了"实测仍 not logged in(可能在别的 shell 跑过,token 没共享过来)。规则:用户说"好了"/"做完了"时,先用工具实测(gh auth status / curl / process list),不要直接信任口头报告。1+N 部署踩过一次。