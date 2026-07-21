Host: Windows 10. User home: C:\Users\Administrator. Shell is git-bash/MSYS (POSIX), NOT PowerShell — use bash syntax (ls, $HOME, &&, |, single quotes, MSYS-style /c/Users/... paths). Python: 3.11.9. Package manager: uv available, pip → python3.11. python3 command is MISSING — always invoke `python` not `python3`.
§
Hermes Agent v0.15.1, config v26, install at C:\Users\Administrator\AppData\Local\hermes\hermes-agent. Active profile: handsome_company_manager. Single model configured: MiniMax-M3 via minimax-cn provider (https://api.minimaxi.com/v1). Agent max_turns: 150, terminal timeout: 180s, compression threshold 50% → 20%.
§
1+N 数字员工集成(2026-07-08):fork 到 Hermes。Skill `~/AppData/Local/hermes/skills/productivity/oneplusn/`,9 个 bash 命令在 `~/AppData/Local/hermes/bin/oneplusn*`(cp 副本,Windows ln-sf 坏),cron 30 分钟 + reaper 1 小时(hermes cron --no-agent)。Eval 10/10 PASS。配套 skill `claude-package-to-hermes-skill` 在 `devops/`,记 .claude 包移植方法论 + Windows 路径陷阱 + bash 包装 + cron + evals 模板。
§
Credential state (2026-07-20): profile `.env` contains `MINIMAX_CN_API_KEY` and `GITHUB_TOKEN`; GitHub CLI is usable. `HF_TOKEN` is present but commented out (inactive). Other provider credentials were not re-validated in this cleanup—do not infer their availability from older snapshots.
§
4-profile Agent Team (pm/eng/qa/ast) at ~/AppData/Local/hermes/profiles/. Kanban dispatcher embedded in gateway (kanban.dispatch_in_gateway=true), 60s tick. Manual at ~/AppData/Local/hermes/USAGE.md. (Validation history + pitfall notes archived 2026-07-09.)
§
PM 铁律+陷阱:(1) PM=派单+管进展,不越俎。(2) Issue closed≠完成,必查 commit+PR merged+抽读+evaluator 无 Write/Edit。(3) 用户口头"好了"/"做完了"必须工具实测再报告。(4) 凭据双链路:boss OAuth 可直 git push 绕 reviewer;员工 PAT 仅 gh API。(5) 永不 in-place sed .env。(6) MSYS:`\\${var}` 不展开、`icacls /T` 禁、`hermes_tools` 拒读 .env。详见 oneplusn references/windows-msys-tooling.md。

PM cron:`pm-bihourly-status-report` job_id=d26c66fbbdd0, `0 */2 * * *`, deliver=feishu home。每 2h 拉真数据生成报告,只观察不干预。