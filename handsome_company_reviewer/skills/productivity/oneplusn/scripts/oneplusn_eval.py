#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
oneplusn_eval.py — 1+N 数字员工系统的自动验收测试。

跑:
    python scripts/oneplusn_eval.py [--work-dir <test-dir>]

只测本地可自动化部分(github / hermes 真实测试留给 on-board 流程中的 --test)。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

import yaml

# 颜色输出
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"

SKILL_DIR = Path("C:/Users/Administrator/AppData/Local/hermes/skills/productivity/oneplusn")
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATES_DIR = SKILL_DIR / "references_agent"
REAPER_SCRIPT = Path("C:/Users/Administrator/AppData/Local/hermes/scripts/oneplusn-reap.sh")

# Windows 兼容:在 Windows 上,Python 调用 subprocess 时需要 Windows 风格路径
# 否则 `/c/...` 会被解释成 `C:\c\...`(错误)
if os.name == "nt":
    SCRIPTS_DIR_WIN = str(SCRIPTS_DIR).replace("/", "\\")
    REAPER_SCRIPT_WIN = str(REAPER_SCRIPT).replace("/", "\\")
else:
    SCRIPTS_DIR_WIN = str(SCRIPTS_DIR)
    REAPER_SCRIPT_WIN = str(REAPER_SCRIPT)


def win_path(p: Path) -> str:
    """Convert a Path to a Windows-style path string for subprocess."""
    if os.name != "nt":
        return str(p)
    # 关键:Path("/c/...") → str → "C:\c\..."(错)
    # 修复:用 absolute path,避免 leading slash 解析
    abs_p = p.resolve()
    return str(abs_p)

results: List[Tuple[str, str, str]] = []  # (test_id, status, message)


def step(test_id: str, desc: str) -> None:
    print(f"\n{CYAN}[{test_id}]{RESET} {desc}")


def pass_(test_id: str, msg: str = "") -> None:
    results.append((test_id, "PASS", msg))
    print(f"  {GREEN}✓{RESET} {msg or 'ok'}")


def fail(test_id: str, msg: str) -> None:
    results.append((test_id, "FAIL", msg))
    print(f"  {RED}✗{RESET} {msg}")


def skip(test_id: str, msg: str) -> None:
    results.append((test_id, "SKIP", msg))
    print(f"  {YELLOW}⊘{RESET} {msg}")


def run_cmd(cmd: list, cwd: Path = None, env: dict = None) -> Tuple[int, str, str]:
    """跑子进程,返回 (rc, stdout, stderr)"""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       env=env or os.environ, timeout=30)
    return p.returncode, p.stdout, p.stderr


# ============================================================
# 准备:搭一个 sandbox work-dir
# ============================================================

def setup_sandbox(work_dir: Path) -> dict:
    """准备 test fixture。返回 handoff 数据。"""
    work_dir.mkdir(parents=True, exist_ok=True)

    handoff = {
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "stage": "team-ready",
        },
        "organization": {
            "name": "test-team",
            "url": "https://github.com/test-team",
        },
        "repository": {
            "name": "agent_workflow",
            "url": "https://github.com/test-team/agent_workflow",
            "issues_url": "https://github.com/test-team/agent_workflow/issues",
        },
        "boss": {
            "github_username": "test-boss",
            "email": "boss@test.local",
        },
        "agents": {
            "test-dev-01": {
                "name": "test-dev-01",
                "role": "developer",
                "agent_type": "hermes",
                "github_username": "test-boss-dev01",
                "github_email": "test-boss+dev01@test.local",
                "gateway_port": 18001,
                "status": "active",
                "onboarded_at": "2026-07-08 16:00:00",
                "soul_source": "agency-agents-zh/engineering/senior-developer.md",
                "cron_frequency": "*/30 * * * *",
                "upgrade_modules": ["hindsight", "search"],
            },
            "test-rev-01": {
                "name": "test-rev-01",
                "role": "reviewer",
                "agent_type": "hermes",
                "github_username": "test-boss-rev01",
                "github_email": "test-boss+rev01@test.local",
                "gateway_port": 18002,
                "status": "active",
                "onboarded_at": "2026-07-08 16:01:00",
                "soul_source": "agency-agents-zh/engineering/code-reviewer.md",
                "cron_frequency": "15,45 * * * *",
            },
        },
    }
    handoff_path = work_dir / "handoff.yaml"
    with open(handoff_path, "w", encoding="utf-8") as f:
        yaml.dump(handoff, f, default_flow_style=False, allow_unicode=True)
    return handoff


# ============================================================
# 测试用例
# ============================================================

def test_handoff_schema(handoff: dict) -> None:
    step("EVAL-01", "handoff.yaml schema 完整")
    required_top = ["metadata", "organization", "repository", "boss"]
    for key in required_top:
        if key not in handoff:
            fail("EVAL-01", f"缺顶层键: {key}")
            return
    if "agents" not in handoff:
        fail("EVAL-01", "缺 agents 节点")
        return
    if not handoff.get("agents"):
        fail("EVAL-01", "agents 不能为空")
        return
    pass_("EVAL-01", f"top keys ok, {len(handoff['agents'])} 个员工")


def test_agent_required_fields(handoff: dict) -> None:
    step("EVAL-02", "每个 agent 字段完整")
    required = [
        "name", "role", "agent_type", "github_username",
        "gateway_port", "status",
    ]
    for name, a in handoff["agents"].items():
        for f in required:
            if f not in a:
                fail("EVAL-02", f"{name} 缺 {f}")
                return
        # 端口范围合理
        port = a.get("gateway_port", 0)
        if not (1024 < port < 65535):
            fail("EVAL-02", f"{name} 端口 {port} 不在合法范围")
            return
        # status 合法
        if a.get("status") not in ("active", "paused", "error"):
            fail("EVAL-02", f"{name} 状态 {a.get('status')} 非法")
            return
    pass_("EVAL-02", f"{len(handoff['agents'])} 个 agent 都字段完整 + 端口合法")


def test_role_valid(handoff: dict) -> None:
    step("EVAL-03", "所有 role 在合法列表中")
    valid_roles = {
        "developer", "reviewer", "architect", "tester",
        "project-manager", "insight-specialist", "research-analyst",
        "security-engineer", "custom",
    }
    for name, a in handoff["agents"].items():
        if a.get("role") not in valid_roles:
            fail("EVAL-03", f"{name} 角色 {a.get('role')} 不在合法列表")
            return
    pass_("EVAL-03", "所有 role 都合法")


def test_sync_generates_readme(work_dir: Path) -> None:
    step("EVAL-04", "sync 生成的 README.md 存在且含团队表")
    script = win_path(SCRIPTS_DIR / "oneplusn_sync.py")
    rc, out, err = run_cmd([
        "python", script, "--work-dir", str(work_dir), "--no-push",
    ], cwd=work_dir)
    if rc != 0:
        fail("EVAL-04", f"sync 失败: rc={rc} err={err[:200]}")
        return
    readme = work_dir / "README.md"
    if not readme.exists():
        fail("EVAL-04", "README.md 未生成")
        return
    content = readme.read_text(encoding="utf-8")
    for marker in ["# test-team", "## 团队", "## 协作全景",
                   "## 当前 Cronjob 状态", "test-dev-01", "test-rev-01"]:
        if marker not in content:
            fail("EVAL-04", f"README 缺关键内容: {marker!r}")
            return
    pass_("EVAL-04", f"README {len(content)} 字节, 含 Mermaid + 团队表 + Cronjob 段")


def test_sync_idempotent(work_dir: Path) -> None:
    step("EVAL-05", "sync 跑两次不会乱(每次 commit 但内容可重现)")
    script = win_path(SCRIPTS_DIR / "oneplusn_sync.py")
    run_cmd(["python", script, "--work-dir", str(work_dir), "--no-push"], cwd=work_dir)
    first = (work_dir / "README.md").read_text(encoding="utf-8")
    run_cmd(["python", script, "--work-dir", str(work_dir), "--no-push"], cwd=work_dir)
    second = (work_dir / "README.md").read_text(encoding="utf-8")
    import re
    a = re.sub(r"v1\.0.*", "v1.0", first)
    b = re.sub(r"v1\.0.*", "v1.0", second)
    if a != b:
        fail("EVAL-05", f"两次跑 README 不一致")
        return
    pass_("EVAL-05", "两次生成模板部分完全一致(仅时间戳不同)")


def test_gitignore_creation(work_dir: Path) -> None:
    step("EVAL-06", "git 仓库里 sync 后 .gitignore 包含敏感路径")
    run_cmd(["git", "init", "-b", "main"], cwd=work_dir)
    script = win_path(SCRIPTS_DIR / "oneplusn_sync.py")
    rc, out, err = run_cmd([
        "python", script, "--work-dir", str(work_dir), "--no-push",
    ], cwd=work_dir)
    if rc != 0:
        fail("EVAL-06", f"sync 失败: rc={rc} err={err[:200]}")
        return
    gitignore = work_dir / ".gitignore"
    if not gitignore.exists():
        fail("EVAL-06", ".gitignore 未创建")
        return
    content = gitignore.read_text(encoding="utf-8")
    for pattern in ["handoff.yaml", "agents/*/.env", "__pycache__/"]:
        if pattern not in content:
            fail("EVAL-06", f".gitignore 缺 {pattern}")
            return
    rc, out, err = run_cmd(["git", "check-ignore", "handoff.yaml"], cwd=work_dir)
    if rc != 0:
        fail("EVAL-06", f"git 没忽略 handoff.yaml(会泄露 token). check-ignore: {out}")
        return
    pass_("EVAL-06", ".gitignore 完整 + git check-ignore 验证通过")


def test_gitignore_idempotent(work_dir: Path) -> None:
    step("EVAL-07", "ensure_gitignore 重复跑不重复添加")
    sys.path.insert(0, str(SCRIPTS_DIR))
    from create_org import ensure_gitignore_for_oneplusn
    ensure_gitignore_for_oneplusn(work_dir)
    before = (work_dir / ".gitignore").read_text(encoding="utf-8")
    count_before = before.count("agents/*/.env")
    ensure_gitignore_for_oneplusn(work_dir)
    after = (work_dir / ".gitignore").read_text(encoding="utf-8")
    count_after = after.count("agents/*/.env")
    if count_before != count_after or count_after != 1:
        fail("EVAL-07", f"agents/*/.env 出现 {count_after} 次(应该 1)")
        return
    pass_("EVAL-07", f"agents/*/.env 出现 {count_after} 次(刚好)")


def test_soul_cache_miss_then_hit(work_dir: Path) -> None:
    step("EVAL-08", "SOUL 缓存:miss → fetch → hit(无网络)")
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["ONEPLUSN_WORK_DIR"] = str(work_dir)

    import importlib
    import onboard_agent
    importlib.reload(onboard_agent)

    # 第一次:cache miss
    r1 = onboard_agent.fetch_soul_preview("developer", "eval-emp-1")
    if r1 is None:
        # 网络失败或 role 不对 — 尝试拿确切错误
        try:
            import onboard_agent as oa
            role_info = oa.ROLE_SOUL_MAP.get("developer")
            print(f"  role_info: {role_info}")
            if role_info:
                content = oa.http_get(role_info["url"])
                print(f"  http_get first 100 chars: {content[:100]!r}")
        except Exception as e:
            print(f"  debug error: {e}")
        fail("EVAL-08", f"fetch_soul_preview 返回 None(可能网络问题)")
        return
    if r1.get("cached") is True:
        fail("EVAL-08", f"第一次应该是 cache miss,得到 {r1.get('cached')}")
        return

    cache = work_dir / "agents" / "eval-emp-1" / "soul-source.md"
    if not cache.exists():
        fail("EVAL-08", f"缓存文件 {cache} 未创建")
        return

    # 第二次:hit
    r2 = onboard_agent.fetch_soul_preview("developer", "eval-emp-1")
    if not r2 or r2.get("cached") is not True:
        fail("EVAL-08", f"第二次应该是 cache hit,得到 {r2.get('cached') if r2 else None}")
        return
    if r1.get("content") != r2.get("content"):
        fail("EVAL-08", "hit 和 miss 内容不一致")
        return
    pass_("EVAL-08", f"miss(网络)→ hit(本地)→ 一致({len(r1.get('content', ''))} 字节)")


def test_reaper_parsing(work_dir: Path) -> None:
    step("EVAL-09", "reaper 解析 handoff 正确找到 PM 候选")
    rc, out, err = run_cmd([
        "bash", REAPER_SCRIPT_WIN,
        str(work_dir / "handoff.yaml"), "60", "--dry-run",
    ], env={**os.environ, "PATH": "/c/Program Files/GitHub CLI:" + os.environ.get("PATH", "")})
    if rc != 0:
        fail("EVAL-09", f"reaper 退出码 {rc}: {err[:200]}")
        return
    if "reassign 给 @test-boss" not in out:
        fail("EVAL-09", f"reaper 输出没显示目标 PM,out: {out[:300]}")
        return
    pass_("EVAL-09", "reaper 解析 handoff + fallback 到 boss OK")


def test_deps_check() -> None:
    step("EVAL-10", "create_org.py --check-deps 能跑通不崩溃")
    rc, out, err = run_cmd([
        "python", str(SCRIPTS_DIR / "create_org.py"),
        "--check-deps", "--platform", "windows",
    ], env={**os.environ, "PATH": "/c/Program Files/GitHub CLI:" + os.environ.get("PATH", "")})
    if rc not in (0, 1):  # 可能因为缺一些东西返回 1,但不该 crash
        fail("EVAL-10", f"crash rc={rc}: {err[:200]}")
        return
    if "hermes" not in out.lower() and "Hermes" not in out:
        fail("EVAL-10", f"输出不像 dep check 报告:{out[:200]}")
        return
    pass_("EVAL-10", f"dep check 跑通(hermes/python/git/gh/PyYAML 列表)")


# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="1+N 数字员工系统 evals")
    ap.add_argument("--work-dir", "-w", default=None,
                    help="测试 work-dir(默认新建临时目录)")
    ap.add_argument("--keep", action="store_true", help="保留测试目录(默认清理)")
    args = ap.parse_args()

    if args.work_dir:
        work_dir = Path(args.work_dir).resolve()
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="oneplusn-eval-")).resolve()

    print(f"{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}  1+N 数字员工系统 — evals{RESET}")
    print(f"{CYAN}  work-dir: {work_dir}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    try:
        handoff = setup_sandbox(work_dir)
        print(f"\n✓ Sandbox 已建,含 {len(handoff['agents'])} 个员工")

        test_handoff_schema(handoff)
        test_agent_required_fields(handoff)
        test_role_valid(handoff)
        test_sync_generates_readme(work_dir)
        test_sync_idempotent(work_dir)
        test_gitignore_creation(work_dir)
        test_gitignore_idempotent(work_dir)
        test_soul_cache_miss_then_hit(work_dir)
        test_reaper_parsing(work_dir)
        test_deps_check()

    finally:
        # 报告
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}  测试结果汇总{RESET}")
        print(f"{CYAN}{'='*60}{RESET}")
        n_pass = sum(1 for _, s, _ in results if s == "PASS")
        n_fail = sum(1 for _, s, _ in results if s == "FAIL")
        n_skip = sum(1 for _, s, _ in results if s == "SKIP")
        n_total = len(results)
        for tid, status, msg in results:
            icon = {"PASS": f"{GREEN}✓{RESET}", "FAIL": f"{RED}✗{RESET}",
                    "SKIP": f"{YELLOW}⊘{RESET}"}[status]
            print(f"  {icon} {tid}: {status:5s} {msg}")
        print(f"\n  通过:{n_pass}/{n_total}  失败:{n_fail}  跳过:{n_skip}")
        rate = n_pass / n_total if n_total else 0
        if rate >= 1.0:
            print(f"  {GREEN}状态:✓ 全部通过,可上岗{RESET}")
        elif rate >= 0.85:
            print(f"  {YELLOW}状态:基本可用,需修复失败项{RESET}")
        else:
            print(f"  {RED}状态:不可用,需排查问题{RESET}")

        # 清理(除非 --keep)
        if not args.keep and not args.work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
            print(f"\n  [已清理测试目录]")

        sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
