#!/usr/bin/env python3
"""
oneplusn poll pre-flight check.

Cheap access probe every cron tick must run BEFORE declaring [SILENT].
Distinguishes three states:
  - OK:        token authenticates AND repo visible          -> poll normally
  - NO_REPO:   token authenticates BUT repo 404              -> log breadcrumb, [SILENT]
  - BAD_PAT:   token does not authenticate (401/403)         -> log breadcrumb, [SILENT]

Usage (called from oneplusn-poll.sh or directly by an LLM-driven cron tick):
    python scripts/poll-preflight.py <agent-profile-name> <org> <repo>

Stdout is JSON: {"status": "OK"|"NO_REPO"|"BAD_PAT", "login": "...", "repo_visible": bool}
Exit 0 always (caller decides what to emit).

Side effect: appends to <profile>/logs/poll-access.log on NO_REPO or BAD_PAT.

Reference: SKILL.md section "Cron polling: pre-flight access check (mandatory)"
           references/employee-repo-access.md
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def gh_json(args, env):
    """Run `gh <args>` and return (exit, stdout, stderr)."""
    p = subprocess.run(["gh"] + args, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def load_token(profile: str):
    """Load GITHUB_TOKEN from the employee's profile .env.

    Tries Windows-style %USERPROFILE%\\AppData\\Local\\hermes\\profiles\\<name>\\.env
    first, then the POSIX-style ~/.hermes/profiles/<name>/.env fallback.
    """
    candidates = [
        Path