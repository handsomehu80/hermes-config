#!/usr/bin/env python
"""
Reusable Hindsight `reflect()` runner for the hermes-memory-hygiene skill.

Usage:
    python scripts/hindsight_reflect.py <profile> [--query "..."] [--bank-id hermes]

What it does:
  1. Loads the profile's .env (MINIMAX_CN_API_KEY, MINIMAX_CN_BASE_URL, ...).
  2. Overrides HINDSIGHT_API_LLM_* env vars BEFORE spawning the daemon
     (avoids the `openai_compatible` Invalid-provider error from config.json).
  3. Clears stale ~/.hindsight/profiles/*.lock files.
  4. Starts the HindsightEmbedded daemon with the correct provider.
  5. Short-circuits if the bank is empty.
  6. Calls reflect() and reports new vs existing mental models.

Exit codes:
  0  - reflect() ran (or bank was empty + we decided not to reflect)
  1  - daemon failed to start (environmental, see log)
  2  - missing API key in profile .env
  3  - HindsightEmbedded not importable. On Windows named-profile installs
       the runner auto-detects this and re-execs to the venv python
       (<hermes-agent>/venv/Scripts/python.exe). If the re-exec also fails
       (no venv python found, or the venv itself is broken), exit 3 is
       returned with a hint pointing at the expected invocation.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

DEFAULT_LLM_MODEL = "MiniMax-M3"
DEFAULT_BANK_ID = "hermes"
DEFAULT_QUERY = "Consolidate the durable knowledge in this bank"


def load_profile_env(profile: str) -> tuple[str, str, str]:
    """Returns (api_key, base_url, llm_model)."""
    # Named Hermes profiles on Windows commonly live under LOCALAPPDATA,
    # while older/Linux installs use ~/.hermes. Prefer an explicitly supplied
    # HERMES_HOME, then search both layouts instead of assuming one.
    roots: list[Path] = []
    if os.environ.get("HERMES_HOME"):
        roots.append(Path(os.environ["HERMES_HOME"]).expanduser())
    roots.extend([
        Path.home() / ".hermes",
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "hermes",
    ])
    env_path = next(
        (root / "profiles" / profile / ".env"
         for root in roots
         if (root / "profiles" / profile / ".env").exists()),
        roots[0] / "profiles" / profile / ".env",
    )
    if not env_path.exists():
        raise FileNotFoundError(f"profile .env not found: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k and v:
            os.environ.setdefault(k, v)
    api_key = os.environ.get("MINIMAX_CN_API_KEY") or os.environ.get("HINDSIGHT_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("no MINIMAX_CN_API_KEY / HINDSIGHT_LLM_API_KEY in profile .env")
    base_url = os.environ.get("MINIMAX_CN_BASE_URL", "https://api.minimaxi.com/v1")
    llm_model = os.environ.get("HINDSIGHT_LLM_MODEL") or DEFAULT_LLM_MODEL
    return api_key, base_url, llm_model


def set_hindsight_env(api_key: str, base_url: str, llm_model: str) -> None:
    """Override Hindsight LLM env vars BEFORE daemon spawn."""
    os.environ["HINDSIGHT_API_LLM_PROVIDER"] = "minimax"  # NOT "openai_compatible"
    os.environ["HINDSIGHT_API_LLM_MODEL"] = llm_model
    os.environ["HINDSIGHT_API_LLM_API_KEY"] = api_key
    os.environ["HINDSIGHT_API_LLM_BASE_URL"] = base_url


def clear_stale_locks() -> int:
    removed = 0
    for lock in glob.glob(os.path.expanduser("~/.hindsight/profiles/*.lock")):
        try:
            os.remove(lock)
            removed += 1
        except OSError:
            pass
    return removed


def find_venv_python() -> str | None:
    """Locate the venv python that has `hindsight` installed.

    On Windows named-profile installs, hindsight lives only in the venv at
    `<hermes-agent>/venv/Lib/site-packages/hindsight/` — NOT in any system
    site-packages. Bare `python` from PATH misses this and the import fails
    with `No module named 'hindsight'`, masking the real HF-blocker signature.

    Returns the absolute path to a different (venv) python interpreter if
    found, else None. The returned path is suitable for `os.execv`.
    """
    candidates: list[Path] = []
    exe = Path(sys.executable).resolve()

    # 1. If we're already inside a venv, prefer that one (covers the case
    #    where the user invoked a different venv python by mistake).
    if exe.parent.name in ("Scripts", "bin"):
        venv_root = exe.parent.parent
        if venv_root.name == "venv":
            candidates.append(venv_root / exe.name)

    # 2. Standard install locations for the Hermes venv.
    hermes_roots: list[Path] = []
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        hermes_roots.append(Path(local_app) / "hermes" / "hermes-agent")
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        hermes_roots.append(Path(hermes_home).parent / "hermes-agent")
    hermes_roots.append(Path.home() / ".local" / "share" / "hermes" / "hermes-agent")
    hermes_roots.append(Path("/usr/local/share/hermes/hermes-agent"))

    for root in hermes_roots:
        if sys.platform == "win32":
            candidates.append(root / "venv" / "Scripts" / "python.exe")
        else:
            candidates.append(root / "venv" / "bin" / "python")

    for cand in candidates:
        if cand and cand.exists() and cand.resolve() != exe:
            return str(cand)
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("profile", help="Hermes profile name, e.g. handsome_company_manager")
    p.add_argument("--bank-id", default=DEFAULT_BANK_ID)
    p.add_argument("--query", default=DEFAULT_QUERY)
    p.add_argument("--idle-timeout", type=int, default=30)
    p.add_argument("--log-level", default="warning")
    args = p.parse_args()

    try:
        api_key, base_url, llm_model = load_profile_env(args.profile)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    set_hindsight_env(api_key, base_url, llm_model)
    n = clear_stale_locks()
    if n:
        print(f"removed {n} stale lock file(s)")

    try:
        from hindsight.embedded import HindsightEmbedded
    except ImportError as e:
        # Likely cause on Windows named-profile installs: hindsight lives only
        # in the venv at <hermes-agent>/venv/Lib/site-packages/hindsight/, but
        # `python` from PATH resolves to a system interpreter that doesn't have
        # it. Try to find the venv python and re-exec to it; this preserves
        # all env vars (including the HINDSIGHT_API_LLM_* overrides) and argv.
        venv_py = find_venv_python()
        if venv_py:
            print(
                f"hindsight not importable from {sys.executable}; "
                f"re-exec'ing to {venv_py}",
                file=sys.stderr,
            )
            os.execv(venv_py, [venv_py, *sys.argv])
            # os.execv does not return on success.
        print(f"ERROR: HindsightEmbedded not importable: {e}", file=sys.stderr)
        print(
            "  Hint: on Windows named-profile installs, hindsight lives only in the venv.",
            file=sys.stderr,
        )
        print(
            "  Try: <hermes-agent>/venv/Scripts/python.exe scripts/hindsight_reflect.py <profile>",
            file=sys.stderr,
        )
        return 3

    print(f"starting daemon for profile={args.profile!r} provider=minimax model={llm_model}")
    try:
        he = HindsightEmbedded(
            profile=args.profile,
            llm_provider="minimax",
            llm_api_key=api_key,
            llm_model=llm_model,
            llm_base_url=base_url,
            idle_timeout=args.idle_timeout,
            log_level=args.log_level,
        )
    except Exception as e:
        # Catches "Invalid LLM provider", daemon-startup failures, port binding
        # errors, and embedded-PostgreSQL / cross-encoder init errors.
        print(f"daemon failed to start: {type(e).__name__}: {e}", file=sys.stderr)
        print("see log: ~/.hindsight/profiles/<profile>.log", file=sys.stderr)
        return 1

    try:
        mems = he.client.list_memories(bank_id=args.bank_id, limit=1)
        mem_list = getattr(mems, "memories", None) or (
            mems.get("memories") if isinstance(mems, dict) else None
        )
        if not mem_list:
            print(f"bank {args.bank_id!r} is empty; nothing to reflect on")
            return 0

        before = he.client.list_mental_models(bank_id=args.bank_id)
        before_ids = {
            getattr(m, "id", None)
            for m in (getattr(before, "mental_models", []) or [])
        }
        print(f"mental_models before: {sorted(i for i in before_ids if i)}")

        he.client.reflect(bank_id=args.bank_id, query=args.query)
        print("reflect() completed")

        after = he.client.list_mental_models(bank_id=args.bank_id)
        after_ids = {
            getattr(m, "id", None)
            for m in (getattr(after, "mental_models", []) or [])
        }
        new_ids = after_ids - before_ids
        if new_ids:
            print(f"NEW mental model(s) created: {sorted(new_ids)}")
        else:
            print("no new mental model created (existing models were updated)")
        return 0
    except Exception as e:
        print(f"reflect() failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            he.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
