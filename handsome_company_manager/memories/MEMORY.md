Host: Windows 10. User home: C:\Users\Administrator. Shell is git-bash/MSYS (POSIX), NOT PowerShell — use bash syntax (ls, $HOME, &&, |, single quotes, MSYS-style /c/Users/... paths). Python: 3.11.9. Package manager: uv available, pip → python3.11. python3 command is MISSING — always invoke `python` not `python3`.
§
Hermes Agent v0.15.1, config v26, install at C:\Users\Administrator\AppData\Local\hermes\hermes-agent. Active profile: default. Single model configured: MiniMax-M3 via minimax-cn provider (https://api.minimaxi.com/v1). Agent max_turns: 150, terminal timeout: 180s, compression threshold 50% → 20%.
§
1+N 数字员工集成(2026-07-08):fork 到 Hermes。Skill `~/AppData/Local/hermes/skills/productivity/oneplusn/`,9 个 bash 命令在 `~/AppData/Local/hermes/bin/oneplusn*`(cp 副本,Windows ln-sf 坏),cron 30 分钟 + reaper 1 小时(hermes cron --no-agent)。Eval 10/10 PASS。配套 skill `claude-package-to-hermes-skill` 在 `devops/`,记 .claude 包移植方法论 + Windows 路径陷阱 + bash 包装 + cron + evals 模板。
§
Configured API keys: only MINIMAX_CN_API_KEY. Missing: OpenRouter, OpenAI, Google, xAI, Exa, Tavily, Firecrawl, Anthropic, GitHub, FAL, ElevenLabs. OAuth providers all unconfigured (Nous/Codex/xAI/Gemini). No GITHUB_TOKEN → 60 req/hr rate limit.
§
4-profile Agent Team (pm/eng/qa/ast) at ~/AppData/Local/hermes/profiles/. Kanban dispatcher embedded in gateway (kanban.dispatch_in_gateway=true), 60s tick. Manual at ~/AppData/Local/hermes/USAGE.md. (Validation history + pitfall notes archived 2026-07-09.)
§
用户口头报告状态 ≠ 实际状态:用户说"我的gh已经登录了"实测仍 not logged in(可能在别的 shell 跑过,token 没共享过来)。规则:用户说"好了"/"做完了"时,先用工具实测(gh auth status / curl / process list),不要直接信任口头报告。1+N 部署踩过一次。
§
1+N 凭据事故(2026-07-13):handsome_company_manager 的 GITHUB_TOKEN 被 sed-i 负例测试擦掉,handoff.yaml 只存 first8,keyring/凭证管家无备份,等老板重粘。规则已写入 oneplusn skill:永不 in-place sed 凭据文件,只允许拷到 /tmp。恢复后立即做:icacls 600 + start.sh 接入 verify_github_identity.sh。
§
PM 团队研究模式 → oneplusn SKILL.md "PM Mode"。

Windows MSYS 陷阱(2026-07-13,详见 oneplusn `references/windows-msys-tooling.md`):(1) `\\${var}` bash 双引号不展开,跑前 `echo $F`。(2) `icacls /T` 禁用于 hermes profile,用 PS `Set-Acl` 单文件。(3) `hermes_tools` 拒读 `.env`,凭据只能 `terminal` inspect。