#!/usr/bin/env python3
"""
数字员工上岗脚本 - 逐个配置 Agent

每次只处理一个数字员工，支持：
- 从 agency-agents-zh 自动匹配 SOUL.md（可预览/编辑）
- README 入职 3 个问题默认答案
- 定时任务默认配置（可修改/添加）
- 自动更新 handoff.yaml 记录员工关系

用法：
    # 交互式模式
    python3 onboard_agent.py --handoff handoff.yaml --interactive

    # 命令行参数
    python3 onboard_agent.py --handoff handoff.yaml \
        --name dev-01 --role developer \
        --github-username oneplusn-dev01 \
        --github-email oneplusn_dev01@163.com \
        --github-token ghp_xxx

    # 测试验证
    python3 onboard_agent.py --handoff handoff.yaml --name dev-01 --test
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# ============ 角色配置 ============

# 角色到 agency-agents-zh SOUL.md 的映射
ROLE_SOUL_MAP = {
    "developer": {
        "file": "engineering/engineering-senior-developer.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/engineering/engineering-senior-developer.md",
        "display": "高级开发工程师",
        "skills": "前端/后端开发、AI集成、Code Review、架构思维、DevOps、数据库设计"
    },
    "reviewer": {
        "file": "engineering/engineering-code-reviewer.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/engineering/engineering-code-reviewer.md",
        "display": "代码审查员",
        "skills": "代码审查、安全漏洞检测、性能优化、设计模式评估、测试覆盖率分析"
    },
    "architect": {
        "file": "engineering/engineering-software-architect.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/engineering/engineering-software-architect.md",
        "display": "软件架构师",
        "skills": "系统设计、微服务、API设计、数据库架构、可扩展性、高可用、安全架构"
    },
    "tester": {
        "file": "testing/testing-embedded-qa-engineer.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/testing/testing-embedded-qa-engineer.md",
        "display": "测试工程师",
        "skills": "测试策略、自动化测试、性能测试、安全测试、CI/CD测试、Bug管理、覆盖率分析"
    },
    "project-manager": {
        "file": "project-management/project-management-project-shepherd.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/project-management/project-management-project-shepherd.md",
        "display": "项目经理",
        "skills": "项目规划、进度跟踪、风险管理、资源协调、团队沟通、需求管理、质量把控"
    },
    "insight-specialist": {
        "file": "strategy/nexus-strategy.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/strategy/nexus-strategy.md",
        "display": "洞察专员",
        "skills": "数据分析、业务洞察、策略建议、可视化呈现、指标体系、预测分析"
    },
    "research-analyst": {
        "file": "academic/academic-literature-reviewer.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/academic/academic-literature-reviewer.md",
        "display": "调研分析师",
        "skills": "用户研究、市场研究、技术调研、文献综述、数据分析、调研报告"
    },
    "security-engineer": {
        "file": "engineering/engineering-security-engineer.md",
        "url": "https://raw.githubusercontent.com/jnMetaCode/agency-agents-zh/main/engineering/engineering-security-engineer.md",
        "display": "安全工程师",
        "skills": "威胁建模、安全审计、渗透测试、漏洞评估、安全架构、应急响应、合规管理"
    }
}

ROLE_CHOICES = list(ROLE_SOUL_MAP.keys()) + ["custom"]


# ============ 工具函数 ============

def log(message: str, level: str = "INFO"):
    prefix = {"INFO": "[ℹ]", "OK": "[✓]", "WARN": "[⚠]", "ERROR": "[✗]", "DRY": "[◌]",
              "STEP": "[→]", "ASK": "[?]"}
    print(f"{prefix.get(level, '[?]')} {message}")


def ask(question: str, default: str = "") -> str:
    try:
        if default:
            response = input(f"  {question} [{default}]: ").strip()
            return response if response else default
        return input(f"  {question}: ").strip()
    except EOFError:
        return default


def ask_bool(question: str) -> bool:
    try:
        while True:
            response = input(f"  {question} (y/n): ").strip().lower()
            if response in ("y", "yes", "是"):
                return True
            if response in ("n", "no", "否", ""):
                return False
            print("    请输入 y 或 n")
    except EOFError:
        return False


def ask_choice(question: str, choices: List[str]) -> int:
    print(f"\n  {question}")
    for i, choice in enumerate(choices, 1):
        print(f"    {i}. {choice}")
    try:
        while True:
            response = ask("请选择", "1")
            try:
                idx = int(response)
                if 1 <= idx <= len(choices):
                    return idx
            except ValueError:
                pass
            print(f"    请输入 1-{len(choices)} 之间的数字")
    except EOFError:
        return 1


def run_cmd(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def http_get(url: str) -> str:
    """HTTP GET 请求。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "oneplusn-onboarding/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return f"# 获取失败: {e}"


def print_email_create_guide(boss_email: str = "") -> str:
    """打印 163 邮箱注册 + SMTP 授权码获取教程。"""
    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║       163 邮箱注册 + SMTP 授权码获取教程                     ║
  ╚══════════════════════════════════════════════════════════════╝

  📧 为什么需要 163 邮箱？
     ──────────────────────────────────────────────────────
     每个数字员工需要一个邮箱地址用于：
     1. 注册 GitHub 账号
     2. 自动发送日报/通知邮件给老板（通过 SMTP）

     推荐使用 163 邮箱：免费、稳定、SMTP 支持好

  📧 方式一：使用 + 别名（推荐，不用注册新邮箱）
     ──────────────────────────────────────────────────────
     如果已有 163 邮箱（如 xxx@163.com），直接用 + 别名：
       - 员工邮箱: xxx+dev01@163.com
       - 原理: + 别名邮件自动转发到原邮箱
       - 一个主邮箱可创建无限多个 + 别名

  📧 方式二：注册全新 163 邮箱
     ──────────────────────────────────────────────────────
     步骤:
       1. 打开 https://mail.163.com/
       2. 点击右侧【注册新账号】
       3. 选择【注册字母邮箱】
       4. 输入用户名（如 oneplusn_team）
          → 完整邮箱: oneplusn_team@163.com
       5. 设置密码（8位以上，大小写+数字）
       6. 输入手机号，获取验证码
       7. 输入验证码，点击【立即注册】

  📧 步骤三：开启 SMTP + 获取授权码
     ──────────────────────────────────────────────────────
     ⚠️ 授权码是数字员工自动发邮件的"密码"，必须获取！

     步骤:
       1. 登录 https://mail.163.com
       2. 右上角【设置】→【POP3/SMTP/IMAP】
       3. 找到【POP3/SMTP服务】→ 点击【开启】
       4. 弹出窗口点击【继续开启】
       5. 按提示发送验证短信（或扫码）
       6. 点击【我已发送】
       7. 系统显示 16 位授权码（如: lunkbrgwqxhfjgxx）
          ⚠️ 只显示一次！立即复制保存！

     SMTP 配置参数:
       服务器: smtp.163.com
       端口: 465（SSL加密）
       用户名: 邮箱地址
       密码: 授权码（不是邮箱登录密码！）

  ══════════════════════════════════════════════════════════════
  """)
    return ""


def print_github_create_guide(name: str, org_name: str, boss_email: str = ""):
    """打印完整的 GitHub 账号创建教程。"""
    suggested_username = f"{org_name}-{name}".lower().replace("_", "-")[:39]
    suggested_alias = ""
    if boss_email and "@" in boss_email:
        local, domain = boss_email.split("@", 1)
        suggested_alias = f"{local}+{name}@{domain}"

    print(f"""
  ╔══════════════════════════════════════════════════════════════╗
  ║            GitHub 账号创建详细教程                            ║
  ╚══════════════════════════════════════════════════════════════╝

  📧 前提：需要先有邮箱地址
     ──────────────────────────────────────────────────────
     如果还没有邮箱，先看上面的【163 邮箱注册教程】
     推荐: {suggested_alias or 'xxx+dev01@163.com'}

  📋 GitHub 注册步骤:
     ──────────────────────────────────────────────────────
       1. 打开 https://github.com/signup
       2. 邮箱: {suggested_alias or '你的 + 别名邮箱'}
       3. 设置密码
       4. 用户名建议: {suggested_username}
       5. 完成验证邮件
       6. 完成人机验证
       7. 选择 "Free" 免费计划
       8. 完成！

  ⚠️ 用户名格式: {org_name}-{name}（如 {suggested_username}）
     只能含字母、数字、连字符

  ══════════════════════════════════════════════════════════════
  """)


def print_pat_create_guide():
    """打印 PAT Token 创建教程。"""
    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║         Personal Access Token (PAT) 创建教程                ║
  ╚══════════════════════════════════════════════════════════════╝

  PAT Token 是数字员工访问 GitHub 的「钥匙」，每个员工需要独立的 Token。

  步骤:
    1. 用员工的 GitHub 账号登录 https://github.com
    2. 点击右上角头像 → Settings
    3. 左侧菜单最下方 → Developer settings
    4. 左侧 → Personal access tokens → Fine-grained tokens
    5. 点击 "Generate new token"
    6. 填写:
       - Token name: oneplusn-{员工名}-token
       - Expiration: 建议选 90 天或 No expiration
       - Description: 1+N 数字员工系统使用
    7. 选择权限（必须勾选）:
       ✅ Repository access → All repositories
       ✅ Repository permissions:
          - Contents: Read and write
          - Issues: Read and write
          - Pull requests: Read and write
       ✅ Organization permissions:
          - Members: Read-only
    8. 点击 "Generate token"
    9. ⚠️ 立即复制 Token！页面关闭后无法再次查看！
       Token 格式: github_pat_xxx 或 ghp_xxx

  ⚠️ 安全提示:
     - Token 只能看一次，务必立即保存
     - 保存在安全的地方（如密码管理器）
     - 不要截图或发送到不安全的聊天

  ══════════════════════════════════════════════════════════════
  """)


def interactive_github_setup(name: str, org_name: str, boss_email: str = "") -> tuple:
    """
    交互式 GitHub 账号配置。
    提供多种选项：已有账号、引导创建新账号、使用 + 别名邮箱。
    返回: (github_username, github_email, github_token)
    """
    print(f"\n{'-'*50}")
    print(f"  GitHub 账号配置 — {name}")
    print(f"{'-'*50}")

    # 前置：确认邮箱是否就绪
    has_ready_email = ask_bool(f"  已有可用于 {name} 的邮箱地址（如 xxx+{name}@163.com）？")
    if not has_ready_email:
        print("\n  [→] 先配置邮箱（163 邮箱注册 + SMTP 授权码）")
        print_email_create_guide(boss_email)
        print("\n  邮箱和授权码就绪后，继续配置 GitHub...")

    while True:
        print(f"""
  请选择 GitHub 账号获取方式：

    [A] 已有账号 — 直接输入用户名/邮箱/Token
    [B] 引导创建 — 显示完整的 GitHub 注册教程
    [C] +别名邮箱 — 用老板邮箱的 + 别名创建（推荐）
    [D] 复用Token — 员工与老板共享 Token（快速但不推荐）
    [Q] 跳过 — 稍后手动配置
        """)

        choice = ask("请选择", "A").strip().upper()

        if choice == "A":
            # 已有账号
            print(f"\n  [A] 使用已有 GitHub 账号")
            github_username = ask("  GitHub 用户名")
            github_email = ask("  绑定的邮箱")
            has_token = ask_bool("  已有 Personal Access Token？")
            if has_token:
                github_token = ask("  Token (ghp_xxx 或 github_pat_xxx)")
            else:
                print("\n  [→] 引导创建 PAT Token...")
                print_pat_create_guide()
                github_token = ask("  创建好的 Token")
            return github_username, github_email, github_token

        elif choice == "B":
            # 引导创建新账号
            print(f"\n  [B] 引导创建新 GitHub 账号")
            print_github_create_guide(name, org_name, boss_email)

            ready = ask_bool("  是否已完成 GitHub 账号注册？")
            if ready:
                github_username = ask("  创建好的用户名")
                github_email = ask("  注册的邮箱")
                print("\n  [→] 接下来需要创建 PAT Token...")
                print_pat_create_guide()
                github_token = ask("  创建好的 Token")
                return github_username, github_email, github_token
            else:
                print("  [ℹ] 请先完成注册，然后重新运行此步骤")
                retry = ask_bool("  已完成，继续？")
                if retry:
                    continue
                return "", "", ""

        elif choice == "C":
            # + 别名邮箱
            print(f"\n  [C] 使用 + 别名邮箱创建")
            if boss_email and "@" in boss_email:
                local, domain = boss_email.split("@", 1)
                suggested = f"{local}+{name}@{domain}"
                print(f"\n  建议邮箱: {suggested}")
                use_suggested = ask_bool(f"  使用建议邮箱 {suggested}？")
                if use_suggested:
                    github_email = suggested
                else:
                    custom_alias = ask("  输入自定义别名（不要@后面的部分）")
                    github_email = f"{local}+{custom_alias}@{domain}"
            else:
                base_email = ask("  请输入基础邮箱（如 xxx@163.com）")
                if "@" in base_email:
                    local, domain = base_email.split("@", 1)
                    github_email = f"{local}+{name}@{domain}"
                else:
                    github_email = ask("  请输入完整邮箱")

            suggested_username = f"{org_name}-{name}".lower().replace("_", "-")[:39]
            print(f"\n  建议用户名: {suggested_username}")
            use_suggested_name = ask_bool(f"  使用建议用户名？")
            if use_suggested_name:
                github_username = suggested_username
            else:
                github_username = ask("  请输入自定义用户名")

            print(f"""
  📋 创建信息汇总：
     用户名: {github_username}
     邮箱: {github_email}
     密码: 你自己设置

  [→] 请按以下步骤注册：
     1. 打开 https://github.com/signup
     2. 邮箱: {github_email}
     3. 设置密码
     4. 用户名: {github_username}
     5. 完成验证
     6. 选 Free 计划
            """)

            ready = ask_bool("  是否已完成注册？")
            if ready:
                print("\n  [→] 接下来创建 PAT Token...")
                print_pat_create_guide()
                github_token = ask("  Token")
                return github_username, github_email, github_token
            else:
                return "", "", ""

        elif choice == "D":
            # 复用老板 Token
            print(f"\n  [D] 复用老板 Token")
            print(f"  ⚠️ 警告: 多个员工共享同一个 Token 会导致：")
            print(f"     - GitHub API 速率限制更容易触发")
            print(f"     - 无法区分不同员工的操作记录")
            print(f"     - 安全性降低")
            print(f"")
            confirm = ask_bool("  确认使用共享 Token？")
            if confirm:
                github_username = ask("  员工 GitHub 用户名（员工仍需自己的 GitHub 账号）")
                github_email = ask("  员工邮箱")
                github_token = ask("  老板的 Token")
                return github_username, github_email, github_token
            else:
                continue

        elif choice == "Q":
            print("  [ℹ] 已跳过 GitHub 配置，后续可手动添加")
            return "", "", ""

        else:
            print("  请输入 A/B/C/D/Q")


def step_header(num: int, total: int, title: str):
    print(f"\n{'='*50}")
    print(f"[{num}/{total}] {title}")
    print(f"{'='*50}")


# ============ SOUL 匹配 + 本地缓存 ============

# 缓存位置:每个员工的 agents/{name}/soul-source.md
# 缓存策略:
#   - 如果已存在 → 直接用本地(避免重新拉 GitHub)
#   - 否则 → 拉远程,存到本地 + 写到员工目录

def find_work_dir_for(name: Optional[str]) -> Optional[Path]:
    """根据 profile 名推 work-dir。优先从环境变量 ONEPLUSN_WORK_DIR 拿,否则 None。"""
    wd = os.environ.get("ONEPLUSN_WORK_DIR")
    if wd and name:
        return Path(wd)
    return None


def get_local_soul_cache_path(name: str) -> Optional[Path]:
    """返回本员工 soul-source.md 的路径(如果存在)。"""
    wd = find_work_dir_for(name)
    if not wd:
        return None
    p = wd / "agents" / name / "soul-source.md"
    if p.exists():
        return p
    return None


def save_local_soul_cache(work_dir: Path, name: str, content: str) -> Path:
    """把刚拉到的 SOUL 缓存到 work-dir/agents/{name}/soul-source.md。

    这样后续 onboard 同一员工(比如删了重建)直接用本地,不再调 GitHub。
    """
    target = work_dir / "agents" / name
    target.mkdir(parents=True, exist_ok=True)
    cache = target / "soul-source.md"
    cache.write_text(content, encoding="utf-8")
    return cache


def fetch_soul_preview(role: str, employee_name: Optional[str] = None) -> Optional[Dict]:
    """从 agency-agents-zh 拉取 SOUL.md 并生成预览。

    缓存策略:
      1. employee_name 给定 + 本地 cache 存在 → 用本地(零网络调用)
      2. 否则拉远程 → 写到 work-dir/agents/{name}/soul-source.md + 返回
    """
    role_info = ROLE_SOUL_MAP.get(role)
    if not role_info:
        return None

    # 1. 优先用本地缓存
    if employee_name:
        cached = get_local_soul_cache_path(employee_name)
        if cached:
            content = cached.read_text(encoding="utf-8")
            log(f"用本地 SOUL 缓存: {cached}", "INFO")
            return {
                "name": role_info["display"],
                "description": role_info["skills"],
                "source_url": role_info["url"],
                "file": role_info["file"],
                "display": role_info["display"],
                "skills": role_info["skills"],
                "content": content,
                "preview": content[:2000],
                "cached": True,
                "cache_path": str(cached),
            }

    # 2. 拉远程
    content = http_get(role_info["url"])
    if content.startswith("# 获取失败"):
        return None

    # 3. 落盘到 work-dir(下一版 onboard 同一员工时直接命中缓存)
    wd = find_work_dir_for(employee_name)
    if wd and employee_name:
        try:
            cache_path = save_local_soul_cache(wd, employee_name, content)
            log(f"SOUL 已缓存到: {cache_path}", "OK")
        except Exception as e:
            log(f"SOUL 缓存失败(不致命):{e}", "WARN")

    preview = content[:2000]
    lines = content.splitlines()

    name = "未知"
    description = ""
    for line in lines[:30]:
        if line.startswith("name:"):
            name = line.replace("name:", "").strip()
        if line.startswith("description:"):
            description = line.replace("description:", "").strip()

    return {
        "name": name or role_info["display"],
        "description": description or role_info["skills"],
        "source_url": role_info["url"],
        "file": role_info["file"],
        "display": role_info["display"],
        "skills": role_info["skills"],
        "content": content,
        "preview": preview,
        "cached": False,
    }


def interactive_soul_match(role: str, employee_name: Optional[str] = None) -> Optional[str]:
    """交互式 SOUL.md 匹配。返回最终确认的 SOUL 内容。"""
    if role == "custom":
        log("自定义角色，请输入角色描述（或直接提供 SOUL.md 内容）：")
        print("  提示：可以描述期望的能力方向，或粘贴完整的 SOUL.md 内容")
        custom_desc = ask("角色描述/SOUL 内容")
        return f"# 自定义角色\n\n{custom_desc}" if custom_desc else None

    soul_info = fetch_soul_preview(role, employee_name)
    if not soul_info:
        log(f"未找到角色 '{role}' 的 SOUL.md，尝试搜索默认值...", "WARN")
        default_content = generate_default_soul(role)
        log("已生成通用默认值")
        if ask_bool("是否使用此默认值？"):
            return default_content
        return None

    # 显示匹配结果
    log(f"已匹配到角色定义: {soul_info['display']}")
    log(f"来源: {soul_info['source_url']}")

    print(f"\n  --- 角色预览 ---")
    print(f"  名称: {soul_info['name']}")
    print(f"  描述: {soul_info['description'][:100]}...")
    print(f"  技能: {soul_info['skills']}")
    print(f"  --- 内容预览（前 800 字符）---")
    print(f"  {soul_info['preview'][:800]}...")
    print(f"  ------------------------")

    # 用户选择
    print(f"\n  选项:")
    print(f"    y - 直接使用此角色定义")
    print(f"    n - 搜索其他角色")
    print(f"    e - 编辑修改后使用")
    choice = ask("请选择", "y").lower()

    if choice == "y":
        return soul_info["content"]
    elif choice == "e":
        log("请提供修改后的 SOUL 内容（或描述修改方向）：")
        edit_desc = ask("修改内容")
        if edit_desc:
            return f"{soul_info['content']}\n\n# 用户自定义修改\n{edit_desc}"
        return soul_info["content"]
    else:
        # 搜索其他角色
        log("可用的角色定义：")
        all_roles = [(k, v["display"], v["skills"]) for k, v in ROLE_SOUL_MAP.items()]
        for i, (key, display, skills) in enumerate(all_roles, 1):
            print(f"    {i}. [{key}] {display} - {skills[:50]}")
        alt_idx = ask_choice("选择替代角色", [f"[{k}] {v['display']}" for k, v in ROLE_SOUL_MAP.items()])
        alt_role = list(ROLE_SOUL_MAP.keys())[alt_idx - 1]
        return interactive_soul_match(alt_role)


def generate_default_soul(role: str) -> str:
    """生成通用默认 SOUL.md。"""
    return f"""# 通用 AI 助手 - {role}

## 你的身份

你是团队中的一名 **{role}** 数字员工。你专注于通过 AI 能力为团队提供高效、专业的支持。

## 核心使命

1. **专业执行** - 按照你的角色定位高质量完成任务
2. **主动协作** - 通过 GitHub Issues 与团队成员保持同步
3. **持续学习** - 从每次交互中提取经验，不断优化工作方式
4. **质量保障** - 交付物符合行业标准，经过自我审查

## 工作规范

- 所有任务通过 GitHub Issues 接收和跟踪
- 及时更新任务状态，阻塞时主动升级
- 通过 Issue 评论及时汇报任务进展
- 从经验中学习，不断进化自身能力

---
*此为通用默认值，建议从 agency-agents-zh 仓库获取更专业的角色定义。*
*访问: https://github.com/jnMetaCode/agency-agents-zh*
"""


# ============ README 入职默认答案 ============

def generate_readme_answers(name: str, role: str, org_name: str, repo_name: str, boss_username: str) -> Dict[str, str]:
    """根据行业最佳实践生成 3 个入职问题的默认答案。"""

    role_desc_map = {
        "developer": "负责软件的设计、开发和维护，确保代码质量和系统稳定性",
        "reviewer": "负责代码审查和质量把控，确保交付物符合标准",
        "architect": "负责系统架构设计和技术选型，保障系统的可扩展性和稳定性",
        "tester": "负责质量保证和测试自动化，确保交付物的可靠性",
        "project-manager": "负责项目进度跟踪、资源协调和风险管理，保障项目按时交付",
        "insight-specialist": "负责数据分析和业务洞察，为团队提供决策支持",
        "research-analyst": "负责调研分析和信息收集，为产品和策略提供依据",
        "security-engineer": "负责安全审计和攻防对抗，保障系统和数据安全",
        "custom": "按照自定义角色定位完成相应工作"
    }

    role_desc = role_desc_map.get(role, role_desc_map["custom"])

    return {
        "q1_role": f"我是 [{name}]，担任团队的 [{role}]。我的主要职责包括：{role_desc}。我向老板（@{boss_username}）汇报工作，与团队其他成员通过 GitHub Issues 协作完成任务。",
        "q2_workflow": f"团队通过 GitHub Issues（https://github.com/{org_name}/{repo_name}/issues）进行任务管理。工作流程为：老板创建 Issue 并分配给我 → 我处理任务并更新状态标签（todo → in-progress → done）→ 完成后提交 PR → 经过审查后合并关闭。我每半小时自动轮询一次新任务。",
        "q3_collaboration": f"我通过 GitHub Issues 的评论与其他成员沟通。当需要协作时，我会在 Issue 中 @ 相关成员。如果遇到阻塞超过 2 小时，我会升级给老板（@{boss_username}）。所有工作成果通过 PR 提交，经过审查后合并。"
    }


# ============ 定时任务默认配置 ============

def get_default_cron_jobs(name: str) -> List[Dict]:
    """获取每个数字员工的 3 个公用定时任务。"""
    return [
        {
            "name": "task-polling",
            "schedule": "0,30 * * * *",
            "action": "github issue scan --assignee self --auto-process",
            "description": "每半小时轮询 GitHub Issue（错峰可选 0,30 / 15,45 / 10,40）"
        },
        {
            "name": "config-backup",
            "schedule": "0 20 * * *",
            "action": f"config backup --to hermes-config/{name} --exclude-env --commit-push",
            "description": "每天20:00备份 hermes config 到 GitHub（排除 .env）"
        },
        {
            "name": "memory-cleanup",
            "schedule": "0 21 * * *",
            "action": "memory cleanup --archive-older-than 30d --hindsight-optimize",
            "description": "每天21:00清理记忆（装了 hindsight 则高级优化）"
        }
    ]


def interactive_cron_config(name: str) -> List[Dict]:
    """交互式定时任务配置。"""
    jobs = get_default_cron_jobs(name)

    print(f"\n  --- 默认定时任务 ---")
    for i, job in enumerate(jobs, 1):
        print(f"    {i}. {job['name']}: {job['schedule']} - {job['description']}")
    print(f"    ---")

    if not ask_bool("是否修改默认配置？"):
        return jobs

    # 修改现有任务
    modified = []
    for job in jobs:
        if ask_bool(f"修改 '{job['name']}' 的配置？"):
            new_schedule = ask(f"  新的调度 ({job['name']})", job["schedule"])
            new_action = ask(f"  新的命令 ({job['name']})", job["action"])
            modified.append({
                "name": job["name"],
                "schedule": new_schedule,
                "action": new_action,
                "description": job["description"]
            })
        else:
            modified.append(job)

    # 添加新任务
    while ask_bool("添加新的定时任务？"):
        new_name = ask("  任务名称")
        new_schedule = ask("  调度表达式 (cron)")
        new_action = ask("  执行命令")
        new_desc = ask("  描述")
        if new_name and new_schedule:
            modified.append({
                "name": new_name,
                "schedule": new_schedule,
                "action": new_action,
                "description": new_desc
            })

    return modified


# ============ handoff.yaml 更新 ============

def update_handoff(handoff_path: str, agent_info: Dict):
    """更新 handoff.yaml，追加数字员工信息。"""
    try:
        with open(handoff_path, 'r') as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}

    # 确保 agents 字段存在
    if "agents" not in data:
        data["agents"] = {}

    # 添加/更新 Agent 信息
    name = agent_info["name"]
    data["agents"][name] = {
        "name": name,
        "role": agent_info["role"],
        "agent_type": agent_info.get("agent_type", "hermes"),
        "github_username": agent_info["github_username"],
        "github_email": agent_info["github_email"],
        "gateway_port": agent_info.get("gateway_port", 0),
        "status": "active",
        "onboarded_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # 更新 metadata
    if "metadata" not in data:
        data["metadata"] = {}
    data["metadata"]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(handoff_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    log(f"handoff.yaml 已更新: 记录了 {name}", "OK")


# ============ 核心上岗逻辑 ============

class Onboarder:
    def __init__(self, handoff: Dict, dry_run: bool = False):
        self.handoff = handoff
        self.dry_run = dry_run
        self.org = handoff.get("organization", {})
        self.repo = handoff.get("repository", {})
        self.boss = handoff.get("boss", {})

    def get_next_port(self) -> int:
        profiles_dir = Path.home() / ".hermes" / "profiles"
        used_ports = set()
        if profiles_dir.exists():
            for p in profiles_dir.iterdir():
                env_file = p / ".env"
                if env_file.exists():
                    for line in env_file.read_text().splitlines():
                        if line.startswith("GATEWAY_PORT="):
                            try:
                                used_ports.add(int(line.split("=", 1)[1]))
                            except ValueError:
                                pass
        port = 8081
        while port in used_ports:
            port += 1
        return port

    def create_profile(self, name: str) -> bool:
        log(f"创建 Profile: {name}")
        profile_dir = Path.home() / ".hermes" / "profiles" / name
        if profile_dir.exists():
            log(f"Profile {name} 已存在", "WARN")
            return True
        if self.dry_run:
            log(f"将创建 Profile: {name}", "OK")
            return True
        rc, _, _ = run_cmd(["hermes", "profile", "create", name, "--clone"])
        if rc == 0:
            log(f"Profile {name} 创建成功", "OK")
            return True
        log(f"Profile {name} 创建失败", "ERROR")
        return False

    def write_env(self, name: str, username: str, email: str, token: str, port: int, role: str) -> bool:
        profile_dir = Path.home() / ".hermes" / "profiles" / name
        env_path = profile_dir / ".env"
        if self.dry_run:
            log(f"将写入 {env_path}", "OK")
            return True
        env_content = f"""# Agent: {name}
# Role: {role}
GITHUB_USERNAME={username}
GITHUB_EMAIL={email}
GITHUB_TOKEN={token}
GATEWAY_PORT={port}
AGENT_NAME={name}
AGENT_ROLE={role}
"""
        try:
            env_path.write_text(env_content)
            os.chmod(env_path, 0o600)
            log(f"已写入 {env_path}", "OK")
            return True
        except Exception as e:
            log(f"写入失败: {e}", "ERROR")
            return False

    def verify_github(self, token: str, expected_username: str) -> bool:
        if self.dry_run or not token:
            return True
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if data.get("login") == expected_username:
                    log(f"GitHub 验证通过: {expected_username}", "OK")
                    return True
                log(f"用户名不匹配", "WARN")
                return False
        except Exception as e:
            log(f"GitHub API 错误: {e}", "WARN")
            return False

    def onboard(self, name: str, role: str, github_username: str, github_email: str,
                github_token: str, port: int, setup_only: bool = False,
                skip_soul: bool = False, skip_readme: bool = False,
                skip_cron: bool = False) -> Dict:
        results = {"name": name, "steps": {}}
        total_steps = 6

        # 第1步：创建 Profile
        step_header(1, total_steps, "创建 Hermes Profile")
        results["steps"]["profile"] = self.create_profile(name)
        if results["steps"]["profile"]:
            self._write_config(name)

        # 第2步：绑定 GitHub
        step_header(2, total_steps, "绑定 GitHub")
        results["steps"]["env"] = self.write_env(name, github_username, github_email, github_token, port, role)
        results["steps"]["github"] = self.verify_github(github_token, github_username)

        # 第3步：注入灵魂
        if not skip_soul and role != "custom":
            step_header(3, total_steps, "注入角色灵魂")
            soul_content = interactive_soul_match(role, name)
            if soul_content:
                log(f"角色灵魂已确认: {ROLE_SOUL_MAP.get(role, {}).get('display', role)}", "OK")
                results["steps"]["soul"] = True
            else:
                results["steps"]["soul"] = False
        else:
            results["steps"]["soul"] = True

        # 第4步：README 入职（仅交互模式）
        if not skip_readme:
            step_header(4, total_steps, "阅读团队 README")
            log("提示：请将 README 内容发送给 Agent，使用 references/prompts.md 中的入职提示词")
            results["steps"]["readme"] = True

        # 第5步：启动 Gateway
        if not setup_only:
            step_header(5, total_steps, "启动 Gateway")
            if self.dry_run:
                log(f"将启动 Gateway on port {port}", "OK")
                results["steps"]["gateway"] = True
            else:
                run_cmd(["hermes", "profile", "use", name])
                rc, _, _ = run_cmd(["hermes", "gateway", "start", "--port", str(port)])
                results["steps"]["gateway"] = (rc == 0)
                if results["steps"]["gateway"]:
                    log(f"Gateway 启动成功 (port {port})", "OK")
                else:
                    log(f"Gateway 启动失败，可稍后手动启动", "WARN")
        else:
            results["steps"]["gateway"] = True

        # 第6步：定时任务
        if not skip_cron:
            step_header(6, total_steps, "配置定时任务")
            log("使用 scripts/setup_cron.py 配置定时任务")
            log("默认配置见 SKILL.md 第8步，可修改/添加")
            results["steps"]["cron"] = True

        # 汇总
        passed = sum(1 for v in results["steps"].values() if v)
        log(f"\n{'='*50}")
        log(f"上岗完成: {passed}/{len(results['steps'])} 步成功")
        log(f"{'='*50}")

        return results

    def _write_config(self, name: str):
        profile_dir = Path.home() / ".hermes" / "profiles" / name
        config_path = profile_dir / "config.yaml"
        if config_path.exists():
            return
        config = """model:
  provider: openai
  name: gpt-4
  temperature: 0.7
  max_tokens: 4096

memory:
  type: vector
  backend: chroma
  persistence: true

skills:
  auto_load: true
  directory: ./skills/
"""
        try:
            config_path.write_text(config)
        except Exception:
            pass


# ============ 交互式模式 ============

def interactive_mode(handoff: Dict, dry_run: bool):
    print("\n" + "=" * 50)
    print("数字员工上岗 - 交互式配置")
    print("=" * 50)

    org_name = handoff.get("organization", {}).get("name", "未知")
    repo_name = handoff.get("repository", {}).get("name", "未知")
    boss_name = handoff.get("boss", {}).get("github_username", "未知")

    print(f"\n子公司信息:")
    print(f"  Organization: {org_name}")
    print(f"  仓库: {repo_name}")
    print(f"  老板: {boss_name}")

    # 显示已上岗员工
    existing_agents = handoff.get("agents", {})
    if existing_agents:
        print(f"\n已上岗员工 ({len(existing_agents)}人):")
        for name, info in existing_agents.items():
            print(f"  - {name} ({info.get('role', '?')})")

    # 第2步：确定身份
    print(f"\n{'-'*50}")
    name = ask("请输入数字员工的名字")
    if not name:
        log("名字不能为空", "ERROR")
        sys.exit(1)

    # 检查是否已存在
    if name in existing_agents:
        log(f"警告: {name} 已在 handoff.yaml 中存在", "WARN")
        if not ask_bool("是否覆盖？"):
            sys.exit(0)

    # 角色选择
    role_choices = [
        "developer (开发工程师)",
        "reviewer (代码审查员)",
        "architect (架构师)",
        "tester (测试工程师)",
        "project-manager (项目经理)",
        "insight-specialist (洞察专员)",
        "research-analyst (调研分析师)",
        "security-engineer (攻防对抗工程师)",
        "custom (自定义)"
    ]
    role_idx = ask_choice("请选择角色", role_choices)
    role_keys = list(ROLE_SOUL_MAP.keys()) + ["custom"]
    role = role_keys[role_idx - 1]

    # GitHub 账号（详细引导流程）
    github_username, github_email, github_token = interactive_github_setup(name, org_name)

    # 端口
    onboarder = Onboarder(handoff, dry_run)
    suggested_port = onboarder.get_next_port()
    port_str = ask(f"Gateway 端口", str(suggested_port))
    try:
        port = int(port_str)
    except ValueError:
        port = suggested_port

    # 确认
    print(f"\n{'='*50}")
    print("配置确认")
    print(f"{'='*50}")
    print(f"  名字: {name}")
    print(f"  角色: {role}")
    print(f"  GitHub: {github_username}")
    print(f"  邮箱: {github_email}")
    print(f"  Token: {'已提供' if github_token else '未提供'}")
    print(f"  端口: {port}")

    if not ask_bool("\n确认并开始上岗？"):
        print("已取消。")
        return

    # 执行上岗
    results = onboarder.onboard(name, role, github_username, github_email, github_token, port)

    # 第5步（交互式特有）：SOUL 注入
    if role != "custom":
        step_header(5, 9, "注入角色灵魂（交互确认）")
        soul_content = interactive_soul_match(role, name)
        if soul_content:
            log(f"角色灵魂已确认", "OK")
            # 写入 SOUL.md
            profile_dir = Path.home() / ".hermes" / "profiles" / name
            soul_path = profile_dir / "SOUL.md"
            if not dry_run:
                soul_path.write_text(soul_content)
                log(f"SOUL.md 已写入: {soul_path}", "OK")

    # 第6步（交互式特有）：README 入职 + 默认答案
    step_header(6, 9, "README 入职（含默认答案）")
    answers = generate_readme_answers(name, role, org_name, repo_name, boss_name)
    print(f"\n  根据行业最佳实践生成的默认答案：")
    print(f"\n  Q1: 你的角色和职责是什么？")
    print(f"  默认: {answers['q1_role'][:80]}...")
    print(f"\n  Q2: 团队的工作流程是怎样的？")
    print(f"  默认: {answers['q2_workflow'][:80]}...")
    print(f"\n  Q3: 如何与其他成员协作？")
    print(f"  默认: {answers['q3_collaboration'][:80]}...")

    if ask_bool("\n  是否使用默认答案？"):
        log("已使用默认答案", "OK")
    else:
        log("请在 Agent 入职时提供自定义答案")

    # 第8步（交互式特有）：定时任务配置
    step_header(8, 9, "配置定时任务")
    cron_jobs = interactive_cron_config(name)
    log(f"已配置 {len(cron_jobs)} 个定时任务", "OK")

    # 选择 Agent 类型
    print(f"\n{'-'*50}")
    log("选择 Agent 框架类型：")
    log("  1. Hermes Agent（当前唯一支持）")
    log("  2. OpenClaw（即将支持）")
    log("  3. Claude Code（即将支持）")
    log("  4. Cursor Agent（即将支持）")
    agent_type_idx = ask("请选择", "1")
    agent_type_map = {"1": "hermes", "2": "openclaw", "3": "claude-code", "4": "cursor-agent"}
    agent_type = agent_type_map.get(agent_type_idx, "hermes")
    if agent_type != "hermes":
        log(f"{agent_type} 尚未支持，将使用 Hermes Agent", "WARN")
        agent_type = "hermes"

    # 第9步：更新 handoff.yaml
    step_header(9, 9, "更新 handoff.yaml")
    agent_info = {
        "name": name,
        "role": role,
        "agent_type": agent_type,
        "github_username": github_username,
        "github_email": github_email,
        "gateway_port": port
    }
    log(f"Agent 类型: {agent_type}", "OK")

    # 后续指引
    print(f"\n{'='*50}")
    print("后续步骤")
    print(f"{'='*50}")
    print(f"  1. 将 {github_username} 加入 GitHub Organization")
    print(f"  2. 使用 prompts.md 中的提示词完成灵魂注入（如未在脚本中完成）")
    print(f"  3. 发送 README 给 Agent 完成入职确认")
    print(f"  4. 运行 --test 验证上岗结果")
    print(f"\n提示词模板见 references/prompts.md")


def load_handoff(path: str) -> Dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(
        description="数字员工上岗脚本 - 逐个配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式配置（推荐）
  %(prog)s --handoff handoff.yaml --interactive

  # 命令行参数
  %(prog)s --handoff handoff.yaml \\
           --name dev-01 --role developer \\
           --github-username oneplusn-dev01 \\
           --github-email oneplusn_dev01@163.com \\
           --github-token ghp_xxx

  # 仅创建 Profile 和 .env
  %(prog)s --handoff handoff.yaml --name dev-01 --setup-only
        """
    )

    parser.add_argument("--handoff", "-H", required=True, help="handoff.yaml 路径")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")
    parser.add_argument("--name", help="Agent 名字")
    parser.add_argument("--role", choices=ROLE_CHOICES, help="Agent 角色")
    parser.add_argument("--github-username", help="GitHub 用户名")
    parser.add_argument("--github-email", help="GitHub 邮箱")
    parser.add_argument("--github-token", default="", help="GitHub Token")
    parser.add_argument("--gateway-port", type=int, help="Gateway 端口")
    parser.add_argument("--agent-type", choices=["hermes", "openclaw", "claude-code", "cursor-agent"],
                        default="hermes", help="Agent 框架类型（默认 hermes）")
    parser.add_argument("--setup-only", action="store_true", help="仅创建 Profile 和 .env")
    parser.add_argument("--test", action="store_true", help="运行测试验证")
    parser.add_argument("--dry-run", action="store_true", help="试运行")
    parser.add_argument("--skip-soul", action="store_true", help="跳过灵魂注入")
    parser.add_argument("--skip-readme", action="store_true", help="跳过 README 入职")
    parser.add_argument("--skip-cron", action="store_true", help="跳过定时任务")

    args = parser.parse_args()

    if not Path(args.handoff).exists():
        log(f"handoff.yaml 不存在: {args.handoff}", "ERROR")
        sys.exit(1)

    handoff = load_handoff(args.handoff)

    if args.test and args.name:
        log(f"测试 Agent: {args.name}")
        log("请运行 references/evals.md 中的测试项")
        return

    if args.interactive:
        interactive_mode(handoff, args.dry_run)
    elif args.name:
        if not args.role or not args.github_username or not args.github_email:
            log("命令行模式需要: --name, --role, --github-username, --github-email", "ERROR")
            sys.exit(1)

        onboarder = Onboarder(handoff, args.dry_run)
        port = args.gateway_port or onboarder.get_next_port()

        results = onboarder.onboard(
            name=args.name, role=args.role,
            github_username=args.github_username,
            github_email=args.github_email,
            github_token=args.github_token,
            port=port, setup_only=args.setup_only,
            skip_soul=args.skip_soul,
            skip_readme=args.skip_readme,
            skip_cron=args.skip_cron
        )

        # 更新 handoff.yaml
        if not args.dry_run:
            agent_info = {
                "name": args.name, "role": args.role,
                "agent_type": args.agent_type,
                "github_username": args.github_username,
                "github_email": args.github_email,
                "gateway_port": port
            }
            update_handoff(args.handoff, agent_info)
    else:
        log("请提供 --interactive 或 --name")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()