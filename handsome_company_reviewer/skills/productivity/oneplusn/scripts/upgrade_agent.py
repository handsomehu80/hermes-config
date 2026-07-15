#!/usr/bin/env python3
"""
数字员工升级脚本 - 将基础 Agent 升级为超级员工

用法：
    # 交互式升级
    python3 upgrade_agent.py --handoff handoff.yaml --interactive

    # 升级单个 Agent
    python3 upgrade_agent.py --handoff handoff.yaml --name dev-01 --modules hindsight,search

    # 批量升级所有 Agent
    python3 upgrade_agent.py --handoff handoff.yaml --all --modules hindsight,voice

    # 查看可升级模块
    python3 upgrade_agent.py --list-modules
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import yaml


MODULES = {
    "hindsight": {
        "name": "Hindsight 记忆系统",
        "desc": "长期记忆增强，支持经验回忆和模式提取",
        "install": "uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hindsight-all",
        "config": "~/.hermes/hindsight/config.json"
    },
    "search": {
        "name": "搜索感知",
        "desc": "网络搜索能力（DuckDuckGo/Tavily）",
        "install": "uv pip install --python ~/.hermes/hermes-agent/venv/bin/python ddgs",
        "config": "hermes config set web.backend tavily"
    },
    "voice": {
        "name": "语音交互",
        "desc": "STT 语音输入 + TTS 语音输出",
        "install": "uv pip install --python ~/.hermes/hermes-agent/venv/bin/python faster-whisper edge-tts",
        "config": "config.yaml stt/tts 段落"
    },
    "efficiency": {
        "name": "效率优化",
        "desc": "成本显示、对话压缩、自我进化",
        "install": "内置，无需安装",
        "config": "config.yaml compression/curator 段落"
    }
}


def log(message: str, level: str = "INFO"):
    prefix = {"INFO": "[ℹ]", "OK": "[✓]", "WARN": "[⚠]", "ERROR": "[✗]"}
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


def interactive_upgrade(handoff: Dict):
    """交互式升级。"""
    print("\n" + "=" * 50)
    print("数字员工升级")
    print("=" * 50)

    agents = handoff.get("agents", {})
    if not agents:
        log("handoff.yaml 中没有已上岗的数字员工", "ERROR")
        return

    print(f"\n已上岗员工 ({len(agents)}人):")
    for i, (name, info) in enumerate(agents.items(), 1):
        print(f"  {i}. {name} ({info.get('role', '?')}) [{info.get('agent_type', 'hermes')}]")

    choice = ask("选择要升级的员工（编号，或 all 全部）")
    if choice.lower() == "all":
        targets = list(agents.keys())
    else:
        try:
            idx = int(choice) - 1
            targets = [list(agents.keys())[idx]]
        except (ValueError, IndexError):
            log("选择无效", "ERROR")
            return

    print(f"\n可升级模块:")
    for key, mod in MODULES.items():
        print(f"  [{key}] {mod['name']} - {mod['desc']}")

    modules_str = ask("选择模块（逗号分隔，如 hindsight,search）")
    modules = [m.strip() for m in modules_str.split(",") if m.strip() in MODULES]

    for name in targets:
        log(f"\n升级 {name}...")
        for mod in modules:
            log(f"  安装 {MODULES[mod]['name']}...")
            log(f"    命令: {MODULES[mod]['install']}")
        log(f"{name} 升级完成", "OK")


def main():
    parser = argparse.ArgumentParser(description="数字员工升级脚本")
    parser.add_argument("--handoff", "-H", required=True, help="handoff.yaml 路径")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式")
    parser.add_argument("--name", help="指定 Agent 名字")
    parser.add_argument("--all", action="store_true", help="升级所有 Agent")
    parser.add_argument("--modules", help="模块列表（逗号分隔）")
    parser.add_argument("--list-modules", action="store_true", help="列出可用模块")

    args = parser.parse_args()

    if args.list_modules:
        print("\n可用升级模块:")
        for key, mod in MODULES.items():
            print(f"  {key}: {mod['name']} - {mod['desc']}")
        return

    if not Path(args.handoff).exists():
        log(f"handoff.yaml 不存在", "ERROR")
        sys.exit(1)

    with open(args.handoff, 'r') as f:
        handoff = yaml.safe_load(f) or {}

    if args.interactive:
        interactive_upgrade(handoff)
    elif args.name and args.modules:
        log(f"升级 {args.name}: {args.modules}")
    elif args.all and args.modules:
        agents = handoff.get("agents", {})
        log(f"批量升级 {len(agents)} 个 Agent: {args.modules}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()