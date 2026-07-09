# Audit session checklist

Tick each box as you complete it. Don't move to the next section until current is complete.

## Before you start
- [ ] Sandbox dir picked (NOT in user's real home; NOT `~/.claude/` or `~/.hermes/`)
- [ ] Original archive preserved separately for comparison
- [ ] Clock the start time (helps estimate effort & find stale assumptions)

## §1 Architecture
- [ ] Top-level README/INDEX read end-to-end
- [ ] Walk every dir declared in diagrams; verify files exist
- [ ] Read frontmatter of every command/skill
- [ ] Dependency tiers mapped (required/recommended/optional)
- [ ] Optional vs. required re-classification written down

## §2 Claims vs. implementation
- [ ] For each "X does Y" claim, found the call site
- [ ] Confirmed whether command `.md` flows through Skill layer or jumps to scripts
- [ ] OS-specific claims tested on actual platform
- [ ] Platform-baked assumptions listed (shebangs, paths, EOL)

## §3 Security
- [ ] Grepped for token/PAT/api_key/secret writes
- [ ] Read every cron/sync/scheduler definition
- [ ] Verified `.env` and `*token*` files excluded from push/backup
- [ ] `.gitignore` audited (handoff.yaml? state.db? *.local.yaml?)
- [ ] Permission scopes vs. claims checked
- [ ] Concurrent-write locations searched for locks

## §4 Runtime test
- [ ] install.sh run; deploy clean
- [ ] `--check-deps` (or equivalent) run; all false +/-s documented
- [ ] Interactive prompts piped with fake stdin (see fake-stdin-pattern.md)
- [ ] Empty / `n` / `y` / garbage inputs tested
- [ ] Milestones reached: handoff, agent onboard, cron, sync
- [ ] Blocked-at-credential steps documented (don't fake)
- [ ] Minimum sane-input set to reach each milestone written down

## §5 Limitations
- [ ] Upstream failure / local fallback analyzed
- [ ] Latency floor / polling cadence captured
- [ ] Collision handling on shared work items checked
- [ ] Cleanup / dead-task / orphan-process recovery story checked
- [ ] Observability: post-mortem capability checked
- [ ] Migration / schema versioning path noted
- [ ] Onboarding path for new operator assessed

## §6 Verdict
- [ ] Three options written: A (adopt as-is), B (fork-and-fix), C (build from-scratch)
- [ ] Effort estimates attached to B if applicable (low/medium/high)
- [ ] User has enough information to pick one with a single letter

## Output format reminder

Number every finding across all sections so the user can refer back:
- §1: A1, A2, ...
- §2: C1, C2, ...
- §3: S1, S2, ...
- §4: R1, R2, ...
- §5: G1, G2, ...
- §6: V1 (the recommended option)

Final response: numbered list + categories + verdict menu. Do NOT auto-pick — wait for user's single-letter reply.
