---
name: bash-cli-wrapper-pattern
description: Cross-platform pattern for a single bash script that doubles as a multi-command CLI (oneplusn / oneplusn-init / oneplusn-status / etc.). Works on macOS, Linux, AND Windows git-bash — including the gotchas around symlink creation, basename dispatch, and `shift` sequencing.
---

# Bash CLI Wrapper Pattern (cross-platform)

A single bash script that supports both invocation styles:

- **`oneplusn init --work-dir <team>`** — the canonical call, with subcommand as the first arg
- **`oneplusn-init --work-dir <team>`** — also works, dispatched by `basename $0`

This pattern evolved from debugging the `oneplusn` integration on Windows + macOS + Linux. Each section is a pitfall with the fix.

---

## 1. Template

```bash
#!/usr/bin/env bash
set -euo pipefail

# ---- 1a. Self-dispatch: symlink/copy basename takes precedence over $1 ----
cmd="${1:-help}"

prog="$(basename "$0")"
if [[ "$prog" == oneplusn-* ]]; then
    # Called via oneplusn-X (copy or symlink). Subcommand = the suffix.
    # DO NOT shift — args after $0 are the subcommand's own args.
    cmd="${prog#oneplusn-}"
else
    # Called via `oneplusn init …`. First arg is the subcommand.
    shift 2>/dev/null || true
fi

case "$cmd" in
    help|-h|--help|"")
        cat <<EOF
Usage:
  oneplusn <subcommand> [args]
  oneplusn-<subcommand> [args]   (alias form)

Subcommands:
  init     ...
  status   ...
  ...
EOF
        ;;
    init)
        ... handle init with "$@" ...
        ;;
    status)
        # Parse --work-dir ourselves; do NOT depend on Python to do it
        WD="."
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --work-dir) WD="$2"; shift 2 ;;
                --work-dir=*) WD="${1#--work-dir=}"; shift ;;
                *) shift ;;
            esac
        done
        ... use "$WD" ...
        ;;
    *)
        echo "[✗] Unknown subcommand: $cmd" >&2
        exit 1
        ;;
esac
```

## 2. Pitfall: `ln -sf` in git-bash on Windows

On Windows under git-bash (MSYS), `ln -sf target linkname` creates something that LOOKS like a symlink (`ls -la` shows `lrwxrwxrwx`) but bash treats it as a regular file when running it — `bash $0` resolves to the **target** path, not the symlink name. This breaks `basename $0` dispatch.

**Verification:**
```bash
ln -sf /tmp/myscript.sh /tmp/myscript-alias
bash /tmp/myscript-alias    # $0 will be /tmp/myscript.sh, NOT /tmp/myscript-alias
```

**Workaround: copy the file, not symlink it.**
```bash
for sub in init add status edit delete; do
    cp myscript.sh "myscript-$sub"
    chmod +x "myscript-$sub"
done
```

This works because bash uses the literal path you invoked, and copies preserve their filenames.

(On macOS and Linux, both `ln -sf` and `cp` work fine for this pattern. Windows is the special case.)

## 3. Pitfall: `shift` sequencing

The naive pattern (shift at the top, then dispatch) loses the first arg when the basename is used:

```bash
# WRONG — loses the workdir arg
cmd="${1:-help}"
shift 2>/dev/null || true   # ALWAYS shifts
prog="$(basename "$0")"
[[ "$prog" == oneplusn-* ]] && cmd="${prog#oneplusn-}"
# Now if called as `oneplusn-status --work-dir /team`:
#   $1 was "--work-dir"  →  cmd = "--work-dir"
#   prog = "oneplusn-status"  →  cmd = "status"  (overwrites)
#   shift already happened →  $1 now "/team", $# = 1
# But the case body parses "$1" as if it were still the first subcommand arg.
```

**Fix: only shift when the subcommand came from `$1`.**
```bash
if [[ "$prog" == oneplusn-* ]]; then
    cmd="${prog#oneplusn-}"
    # do NOT shift
else
    shift 2>/dev/null || true
fi
```

Now:
- `oneplusn status --work-dir /team` → `$1 = "--work-dir"` (untouched), `$# = 2` after this conditional
- `oneplusn-status --work-dir /team` → `$1 = "--work-dir"` (untouched), `$# = 2`

Both paths leave the subcommand args intact for the case body to parse.

## 4. Pitfall: `set -e` + empty `case` body

With `set -euo pipefail`, an empty `case` pattern body can exit the script before the next case branch runs (depends on bash version). Always put a no-op command (`:`) in patterns that should do nothing:

```bash
case "$prog" in
    myscript) :;;            # explicit no-op, safe under set -e
    myscript-*) cmd="...";;
esac
```

## 5. Pitfall: `--work-dir` parsing inside case body

If you re-parse `--work-dir` inside each case body, every case body becomes a mini CLI parser. Cleaner: parse once at the top into shell vars, then case bodies just use them.

For subcommands that need different arg sets (e.g. `init` needs `--boss-email`, `status` only needs `--work-dir`), parse the common flags at the top and let each case body parse its own specifics:

```bash
WD="."
while [[ $# -gt 0 ]]; do
    case "$1" in
        --work-dir) WD="$2"; shift 2 ;;
        --work-dir=*) WD="${1#--work-dir=}"; shift ;;
        *) break ;;     # stop on first non-common arg
    esac
done
```

Now each case body sees `$1` as its first subcommand-specific arg, not `--work-dir`.

## 6. Path portability: `$OSTYPE` for Windows

Detect Windows MSYS / Cygwin and add `gh` to PATH (often missing from default bash PATH on Windows):

```bash
case "$OSTYPE" in
    msys*|cygwin*|win32*) export PATH="/c/Program Files/GitHub CLI:$PATH" ;;
esac
```

## 7. The mental model

Think of the script as a router:

```
                 ┌────────────────────┐
invocation ───►  │  parse subcommand  │ ───►  case body for that subcommand
                 └────────────────────┘
                        ▲
                        │
              prog = basename $0
              OR   $1 (if prog is the master name)
```

The dispatch (steps 1-4) is the same regardless of which invocation style the user picks. Subcommand bodies should treat the remaining args as a normal CLI — they don't care how the user got there.

## 8. Companion: where this lives in `oneplusn`

The script this pattern is based on is `~/AppData/Local/hermes/bin/oneplusn`. The compiled lessons above were extracted AFTER the integration was tested end-to-end. If you're building a similar multi-command bash wrapper, copy the structure from `oneplusn` and the `references/bash-cli-wrapper-pattern.md` pitfalls together.
