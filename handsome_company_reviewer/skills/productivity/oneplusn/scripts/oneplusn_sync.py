#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
oneplusn_sync.py — 重新生成 README.md 并(可选)推送到 GitHub。

用法:
    python oneplusn_sync.py --work-dir <team> [--no-push]

读:
  - {work-dir}/handoff.yaml
  - {skill}/references_agent/readme-template.md

写:
  - {work-dir}/README.md

git:
  - 如果不是 git 仓库,init 一个
  - git add README.md
  - git commit -m "..."
  - git push origin main(除非 --no-push)
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


def find_skill_root() -> Path:
    """找 skill 根目录"""
    here = Path(__file__).resolve().parent
    if (here.parent / "SKILL.md").exists():
        return here.parent
    # 兜底:常见位置
    for cand in [
        Path.home() / "AppData/Local/hermes/skills/productivity/oneplusn",
        Path.home() / ".local/share/hermes/skills/productivity/oneplusn",
    ]:
        if (cand / "SKILL.md").exists():
            return cand
    sys.exit("[✗] 找不到 skill 根目录")


def load_handoff(work_dir: Path) -> dict:
    handoff_path = work_dir / "handoff.yaml"
    if not handoff_path.exists():
        sys.exit(f"[✗] 找不到 {handoff_path}\n    提示: 先 oneplusn init --work-dir <team>")
    with open(handoff_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_template(template: str, handoff: dict, generated_at: str) -> str:
    """模板替换 + 团队表注入"""
    org = handoff.get("organization", {}).get("name", "yourname-team")
    repo = handoff.get("repository", {}).get("name", "agent_workflow")
    boss_username = handoff.get("boss", {}).get("github_username", "yourname-boss")
    boss_email = handoff.get("boss", {}).get("email", "boss@example.com")

    # 简单 {{KEY}} 替换
    out = template
    subs = {
        "{{TEAM_NAME}}": org,
        "{{ORG}}": org,
        "{{REPO}}": repo,
        "{{ORG_NAME}}": org,
        "{{REPO_NAME}}": repo,
        "{{BOSS_USERNAME}}": boss_username,
        "{{BOSS_EMAIL}}": boss_email,
    }
    for k, v in subs.items():
        out = out.replace(k, v)

    # 替换 footer 日期 + 版本
    out = out.replace("v1.0", f"v1.0 | {generated_at}")

    # 在底部 footer 之前插入团队表(找最后一行 '---' 后跟 '*本文档' 的位置)
    team_table = build_team_table(handoff)
    cronblock = build_cronblock(handoff)
    out = inject_before_footer(out, team_table + "\n\n" + cronblock)

    return out


def build_team_table(handoff: dict) -> str:
    agents = handoff.get("agents") or {}
    if not agents:
        return "## 团队\n\n(暂无已上岗员工 — 跑 `oneplusn add` 来添加)\n"
    lines = [
        "## 团队",
        "",
        "| 名字 | GitHub | 邮箱 | 角色 | Agent 类型 | 端口 | 升级模块 | 状态 |",
        "|------|--------|------|------|----------|------|----------|------|",
    ]
    for name, a in agents.items():
        gh_user = a.get("github_username", "—")
        email = a.get("github_email", "—")
        role = a.get("role", "—")
        agent = a.get("agent_type", "—")
        port = a.get("gateway_port", "—")
        mods = ", ".join(a.get("upgrade_modules") or []) or "—"
        status = a.get("status", "—")
        lines.append(
            f"| {name} | @{gh_user} | {email} | {role} | {agent} | {port} | {mods} | {status} |"
        )
    return "\n".join(lines) + "\n"


def build_cronblock(handoff: dict) -> str:
    org = handoff.get("organization", {}).get("name", "ORG")
    repo = handoff.get("repository", {}).get("name", "REPO")
    agents = handoff.get("agents") or {}
    if not agents:
        return ""
    lines = [
        "## 当前 Cronjob 状态",
        "",
        "| 员工 | 轮询频率 | 备注 |",
        "|------|---------|------|",
    ]
    for name, a in agents.items():
        freq = a.get("cron_frequency", "*/30 * * * *")
        lines.append(f"| {name} | `{freq}` | 跑 `oneplusn-poll.sh {name} {org} {repo}` |")
    return "\n".join(lines) + "\n"


def inject_before_footer(md: str, block: str) -> str:
    """在 `---` 跟 `*本文档` 之间插入 block。返回新 md。"""
    marker = "---"
    idx = md.rfind(marker)
    if idx < 0:
        return md + "\n\n" + block
    return md[:idx] + block + "\n" + md[idx:]


def git_step(work_dir: Path, message: str, no_push: bool) -> None:
    """git init / add / commit / push,如需要"""
    # 先 init(配置依赖 .git 目录存在)
    if not (work_dir / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=work_dir, check=True,
                       capture_output=True)
        print(f"[→] git init 完成 (新建仓库)")

    # 确保本地 user.name / user.email(否则 commit 失败)
    cfg = subprocess.run(["git", "config", "user.name"], cwd=work_dir,
                         capture_output=True, text=True)
    if not cfg.stdout.strip():
        boss_email = "boss@oneplusn.local"  # 后置会从 handoff 拿真邮箱
        boss_user = "oneplusn-boss"
        try:
            with open(work_dir / "handoff.yaml", encoding="utf-8") as f:
                h = yaml.safe_load(f)
                boss_email = h.get("boss", {}).get("email", boss_email)
                boss_user = h.get("boss", {}).get("github_username", boss_user)
        except Exception:
            pass
        subprocess.run(["git", "config", "user.name", boss_user], cwd=work_dir, check=True)
        subprocess.run(["git", "config", "user.email", boss_email], cwd=work_dir, check=True)
        print(f"[→] git user 配置:{boss_user} <{boss_email}>")

    # status --porcelain:返回 changed files
    res = subprocess.run(["git", "status", "--porcelain", "README.md"],
                         cwd=work_dir, capture_output=True, text=True)
    if not res.stdout.strip():
        print("[i] README.md 没有变化,跳过 commit")
        return

    subprocess.run(["git", "add", "README.md"], cwd=work_dir, check=True,
                   capture_output=True)
    res = subprocess.run(["git", "commit", "-m", message], cwd=work_dir,
                         capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[✓] git commit 完成: {message}")
    else:
        print(f"[✗] git commit 失败:{res.stderr.strip()[:200]}")
        return

    if no_push:
        print("[i] --no-push,跳过 git push")
        return

    # push 失败不让整个 sync 失败
    res = subprocess.run(["git", "push", "origin", "main"],
                         cwd=work_dir, capture_output=True, text=True)
    if res.returncode == 0:
        print("[✓] git push origin main")
    else:
        print(f"[⚠] git push 失败:{res.stderr.strip()[:200]}")
        print("    本地 commit 已完成,手动 push 即可")


def main():
    ap = argparse.ArgumentParser(description="从 handoff.yaml 重新生成 README")
    ap.add_argument("--work-dir", "-w", required=True, help="团队工作目录")
    ap.add_argument("--no-push", action="store_true", help="只生成本地 README,不 push")
    ap.add_argument("--message", "-m", default=None, help="git commit message")
    args = ap.parse_args()

    work_dir = Path(args.work_dir).resolve()
    if not work_dir.is_dir():
        sys.exit(f"[✗] work-dir 不存在: {work_dir}")

    skill_root = find_skill_root()
    template_path = skill_root / "references_agent" / "readme-template.md"
    if not template_path.exists():
        sys.exit(f"[✗] 找不到模板: {template_path}")

    handoff = load_handoff(work_dir)
    template = template_path.read_text(encoding="utf-8")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rendered = render_template(template, handoff, now)

    out_path = work_dir / "README.md"
    out_path.write_text(rendered, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"[✓] README.md 已生成: {out_path} ({size_kb:.1f} KB)")

    n_agents = len(handoff.get("agents") or {})
    print(f"    含:协作 Mermaid 图 + 团队表格({n_agents} 人) + 5 条核心规则 + Cronjob 状态")

    msg = args.message or f"更新团队 README ({now})"
    git_step(work_dir, msg, args.no_push)

    # 自动 gitignore:必须是 git 仓库(刚 init 完),所以 .git 已存在
    sys.path.insert(0, str(Path(__file__).parent))
    from create_org import ensure_gitignore_for_oneplusn
    ensure_gitignore_for_oneplusn(work_dir)
    # 如果 gitignore 是新加的,补一次 commit + 显式 add 让 git 真的用它
    if (work_dir / ".gitignore").exists():
        r1 = subprocess.run(["git", "add", "-f", ".gitignore"], cwd=work_dir,
                             capture_output=True, text=True)
        if r1.returncode == 0:
            subprocess.run(["git", "commit", "-m", "自动加 .gitignore 保护敏感路径"],
                           cwd=work_dir, capture_output=True, text=True)
        else:
            print(f"[⚠] git add .gitignore 失败: {r1.stderr[:200]}")


if __name__ == "__main__":
    main()
