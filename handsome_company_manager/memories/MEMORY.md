Host: Windows 10. User home: C:\Users\Administrator. Shell is git-bash/MSYS (POSIX), NOT PowerShell — use bash syntax (ls, $HOME, &&, |, single quotes, MSYS-style /c/Users/... paths). Python: 3.11.15 (2026-10-29 实测). Package manager: uv available, pip → python3.11. python3 command is MISSING — always invoke `python` not `python3`.

§

Hermes Agent v0.20.0, install at C:\Users\Administrator\AppData\Local\hermes\hermes-agent. Active profile: handsome_company_manager. Default model: glm-5.2 via zai provider (https://open.bigmodel.cn/api/coding/paas/v4). Agent max_turns: 150.

§

Credential state (2026-10-29): profile `.env` contains `MINIMAX_CN_API_KEY` and `GITHUB_TOKEN`; GitHub CLI is usable. `HF_TOKEN` is present but commented out (inactive). Other provider credentials were not re-validated in this cleanup—do not infer their availability from older snapshots.

§

3-profile Agent Team (PM manager/dev developer/reviewer) at ~/AppData/Local/hermes/profiles/. Kanban dispatcher embedded in gateway (kanban.dispatch_in_gateway=true, tick 60s, verified 2026-10-29). Manual at ~/AppData/Local/hermes/USAGE.md. (Older "4-profile pm/eng/qa/ast" claim corrected 2026-08-16 — disk has 3 profile dirs; history archived 2026-07-09.)

§

PM 铁律+陷阱:(1) PM=派单+管进展,不越俎。(2) Issue closed≠完成,必查 commit+PR merged+抽读+evaluator 无 Write/Edit。(3) 用户口头"好了"/"做完了"必须工具实测再报告。(4) 凭据双链路:boss OAuth 可直 git push 绕 reviewer;员工 PAT 仅 gh API。(5) 永不 in-place sed .env。(6) MSYS:`\\${var}` 不展开、`icacls /T` 禁、`hermes_tools` 拒读 .env。详见 oneplusn references/windows-msys-tooling.md。

PM cron(2026-10-29 复核):5 职=bihourly `0 */2`、daily-evening `0 15`(feishu)、task-polling `15,45`、config-backup `0 20`、memory-cleanup `0 21`(local)。事件史:9-13/9-14 zai 429 击落 3 报告职→9-14 网关 UNCLEANLY 死亡~31d→10-15 02:49 重启补发,5 职全恢复。10-18..20 击落 memory-cleanup 3 fire(重置点 10-21 12:03)→10-21..23 自愈三晚→10-24..27 再击落 4 fire(重置点 10-28 12:03,两次重置恰差 7d=周配额坐实;仅此职受击,其余 4 职 last=ok)→10-28..29 连续两晚恢复(10-29 为本 fire 复核)。429 瞬时型自愈、配额型可击落整 fire、memory-cleanup 为周期性唯一受害者。双小时报告只观察不干预。