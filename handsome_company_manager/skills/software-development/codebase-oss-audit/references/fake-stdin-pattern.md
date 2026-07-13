# Fake stdin pattern for testing interactive CLIs

When auditing a tool that uses `input()` or `read -r` prompts, you cannot let it sit waiting for a human. Build a canned stdin file and pipe it.

## Template

```bash
cat > /tmp/audit_input.txt << 'EOF'
y           # Q1 answer (yes/no)
value-1     # Q2 free-form input
2           # Q3 multiple choice → pick option 2
n           # Q4 answer (no)
EOF
python scripts/interactive.py < /tmp/audit_input.txt 2>&1 | tee /tmp/audit_output.txt
```

Use single-quoted heredoc (`'EOF'`) so the shell does NOT expand `$variables` in your input — you want literal text delivered to the script.

## What to test

| Input        | Purpose                                            | Expected bad behavior             |
|--------------|----------------------------------------------------|-----------------------------------|
| empty line   | verify default kicks in                            | sticks waiting for non-empty      |
| single `n`   | no for y/n prompts                                  | misinterpreted as value           |
| single `y`   | yes for y/n prompts                                 | used as filename by accident     |
| `root@email` | email with `@`                                     | accepted; verify domain exists    |
| `not-email`  | email without `@`                                   | should REJECT; many scripts don't |
| `y\n` extra  | extra y after a confirmation                        | silent default-input collision    |
| long string  | max-length edge                                     | buffer overflow / truncation      |
| `\x00` null  | binary safety                                      | often crashes Python `input()`   |
| rapid repeated | state-machine persistence across calls           | race conditions                   |

## Tracing what happened

After running, search the output for evidence of which prompts were answered how:

```bash
grep -nE "(请输入|请选择|确认|是否|^[?])" /tmp/audit_output.txt
grep -nE "(FAIL|ERROR|Traceback|未安装|失败)" /tmp/audit_output.txt
```

If `peek` into what was being asked, also check what the script logged AFTER each prompt — a script that says "已使用默认值 'y'" and writes handoff.yaml with `name: y` is your smoking gun.

## Don't fake credentials

When the system reaches the GitHub / OAuth / API-key prompt, STOP and document:

> This step requires real credentials I cannot provide. To complete §4 of the audit, run interactively with your own <tokens> and continue from the output.

This is correct protocol — faking `gh auth login` or `gcloud auth` writes to the host filesystem and may pollute later audits.
