#!/usr/bin/env python3
"""
单个数字员工的定时任务配置脚本

每个数字员工自动创建 3 个公用 cronjob：
    1. task-polling   每半小时轮询一次 GitHub Issue（错峰可选：0,30 / 15,45 / 10,40）
    2. config-backup  每天 20:00 备份 hermes config 到 GitHub hermes-config/<name>/（排除 .env）
    3. memory-cleanup 每天 21:00 清理记忆（装了 hindsight 则做高级优化）

用法：
    # 为指定 Profile 配置 3 个默认 cronjob
    python3 setup_cron.py --profile dev-01

    # 自定义轮询错峰（两个分钟点）
    python3 setup_cron.py --profile dev-01 --poll 15,45

    # 完全自定义
    python3 setup_cron.py --profile dev-01 \\
        --poll "10,40 * * * *" \\
        --backup "0 20 * * *" \\
        --cleanup "0 21 * * *"

    # 列出当前任务
    python3 setup_cron.py --profile dev-01 --list

    # 移除所有任务
    python3 setup_cron.py --profile dev-01 --remove-all
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


@dataclass
class CronJob:
    name: str
    schedule: str
    prompt: str  # hermes v0.16+ 的 cron 任务执行的是自然语言 prompt（由 agent LLM 执行）
    params: Dict = field(default_factory=dict)
    description: str = ""


class CronManager:
    """管理单个 Agent 的定时任务。"""

    CRON_PATTERN = re.compile(
        r'^([0-9,*/-]+|\*|\*/[0-9]+)\s+'
        r'([0-9,*/-]+|\*|\*/[0-9]+)\s+'
        r'([0-9,*/-]+|\*|\*/[0-9]+)\s+'
        r'([0-9,*/-]+|\*|\*/[0-9]+)\s+'
        r'([0-9,*/-]+|\*|\*/[0-9]+)$'
    )

    NL_PATTERNS = {
        "每半小时": "0,30 * * * *",
        "每30分钟": "0,30 * * * *",
        "每小时": "0 * * * *",
        "每天": "0 0 * * *",
        "每天早上": "0 8 * * *",
        "每天中午": "0 12 * * *",
        "每天晚上": "0 18 * * *",
        "每天晚上8点": "0 20 * * *",
        "每天晚上9点": "0 21 * * *",
        "每天凌晨": "0 2 * * *",
    }

    # 轮询错峰预设：每半小时一次，仅错开分钟点
    POLL_PRESETS = {
        "0,30": "0,30 * * * *",
        "15,45": "15,45 * * * *",
        "10,40": "10,40 * * * *",
    }

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def log(self, message: str, level: str = "INFO"):
        prefix = {"INFO": "[ℹ]", "OK": "[✓]", "WARN": "[⚠]", "ERROR": "[✗]", "DRY": "[◌]"}
        print(f"{prefix.get(level, '[?]')} {message}")

    def nl_to_cron(self, natural: str) -> str:
        for pattern, cron in self.NL_PATTERNS.items():
            if pattern in natural:
                return cron
        return natural

    def normalize_poll(self, value: str) -> str:
        """把轮询错峰简写（0/30、15/45、10,40）归一化为完整 cron。

        用户用 `m1/m2` 或 `m1,m2` 表示「每半小时一次、错开到这两个分钟点」，
        并非 cron 的 step 语义，因此统一转成 `m1,m2 * * * *`。
        """
        value = value.strip()
        # 简写：两个分钟点，用 / 或 , 分隔（如 0/30、15,45）
        m = re.fullmatch(r'\s*([0-5]?\d)\s*[/,]\s*([0-5]?\d)\s*', value)
        if m:
            return f"{int(m.group(1))},{int(m.group(2))} * * * *"
        if value in self.POLL_PRESETS:
            return self.POLL_PRESETS[value]
        return self.nl_to_cron(value)

    def run_hermes(self, cmd: List[str]) -> Tuple[int, str, str]:
        """运行 hermes 命令。Profile 通过子命令的 --profile 标志指定，不再用 `profile use`。"""
        if self.dry_run:
            self.log(f"将执行: hermes {' '.join(cmd)}", "DRY")
            return 0, "", ""
        try:
            result = subprocess.run(["hermes"] + cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)

    def add_job(self, profile: str, job: CronJob) -> bool:
        if self.dry_run:
            self.log(f"[{profile}] 将添加: {job.name} ({job.schedule})", "DRY")
            return True

        # hermes v0.16+: cron create <schedule> <prompt> --name --profile
        # schedule 与 prompt 是位置参数，profile 是标志；不再有 --command/--schedule。
        rc, stdout, stderr = self.run_hermes([
            "cron", "create",
            job.schedule,
            job.prompt,
            "--name", f"{profile}-{job.name}",
            "--profile", profile,
        ])

        if rc == 0:
            self.log(f"[{profile}] {job.name} 已添加", "OK")
            return True
        else:
            self.log(f"[{profile}] {job.name} 添加失败: {stderr.strip() or stdout.strip()}", "ERROR")
            return False

    def list_jobs(self, profile: str) -> List[Dict]:
        """解析 hermes v0.16+ 的块状 cron list 输出。

        每个任务形如：
            <job_id> [active]
              Name:      <profile>-<job>
              Schedule:  0,30 * * * *
              ...
        仅返回属于该 profile 的任务（按 Name 前缀过滤）。
        """
        rc, stdout, _ = self.run_hermes(["cron", "list"])
        if rc != 0:
            return []
        jobs: List[Dict] = []
        cur: Dict = {}
        id_re = re.compile(r'^([0-9a-f]{6,})\s+\[')
        for line in stdout.splitlines():
            m = id_re.match(line.strip())
            if m:
                if cur.get("name"):
                    jobs.append(cur)
                cur = {"id": m.group(1), "name": "", "schedule": ""}
            elif cur:
                s = line.strip()
                if s.startswith("Name:"):
                    cur["name"] = s.split(":", 1)[1].strip()
                elif s.startswith("Schedule:"):
                    cur["schedule"] = s.split(":", 1)[1].strip()
        if cur.get("name"):
            jobs.append(cur)
        prefix = f"{profile}-"
        return [j for j in jobs if j["name"].startswith(prefix)]

    def remove_all(self, profile: str) -> bool:
        """逐个移除该 profile 的任务（v0.16 的 remove 只接受单个 job_id，无 --all）。"""
        if self.dry_run:
            self.log(f"[{profile}] 将移除所有任务", "DRY")
            return True
        ok_all = True
        for job in self.list_jobs(profile):
            rc, _, stderr = self.run_hermes(["cron", "remove", job["id"]])
            if rc == 0:
                self.log(f"[{profile}] 已移除 {job['name']} ({job['id']})", "OK")
            else:
                self.log(f"[{profile}] 移除 {job['name']} 失败: {stderr.strip()}", "ERROR")
                ok_all = False
        return ok_all

    def setup_defaults(self, profile: str, poll: str, backup: str, cleanup: str):
        """配置每个数字员工的 3 个公用 cronjob。"""
        self.log(f"\n为 {profile} 配置定时任务")
        self.log(f"{'='*40}")

        jobs = [
            CronJob(
                "task-polling",
                self.normalize_poll(poll),
                "轮询分配给你的 GitHub Issue：扫描 assignee 为自己的 open issue，"
                "对有新反馈的逐个处理；没有任务则静默退出，不发送任何通知。",
                {},
                "每半小时轮询 GitHub Issue",
            ),
            CronJob(
                "config-backup",
                self.nl_to_cron(backup),
                f"备份 Hermes 配置到 GitHub 仓库 hermes-config/{profile}/，"
                "排除 .env 等敏感文件，完成后 commit 并 push。回复备份结果（成功/失败 + 备份了哪些文件）。",
                {},
                "备份 hermes config 到 GitHub（排除 .env）",
            ),
            CronJob(
                "memory-cleanup",
                self.nl_to_cron(cleanup),
                "清理你的记忆：归档 30 天前的旧记忆；若安装了 hindsight，调用其优化能力做高级整理。",
                {},
                "记忆清理（装了 hindsight 则高级优化）",
            ),
        ]

        for job in jobs:
            self.add_job(profile, job)

        self.log(f"\n完成。当前任务:")
        for job in self.list_jobs(profile):
            self.log(f"  - {job['name']}: {job['schedule']}")


def main():
    parser = argparse.ArgumentParser(description="数字员工定时任务配置")
    parser.add_argument("--profile", "-p", help="Agent Profile 名称")
    parser.add_argument("--config", "-c", help="cron-config.yaml 路径")
    parser.add_argument("--poll", default="0,30", help="Issue 轮询错峰：0,30 / 15,45 / 10,40 或完整 cron")
    parser.add_argument("--backup", default="0 20 * * *", help="config 备份时间（默认每天 20:00）")
    parser.add_argument("--cleanup", default="0 21 * * *", help="记忆清理时间（默认每天 21:00）")
    parser.add_argument("--list", action="store_true", help="列出当前任务")
    parser.add_argument("--remove-all", action="store_true", help="移除所有任务")
    parser.add_argument("--dry-run", action="store_true", help="试运行")

    args = parser.parse_args()

    manager = CronManager(dry_run=args.dry_run)

    if args.list and args.profile:
        jobs = manager.list_jobs(args.profile)
        for job in jobs:
            print(f"  {job['name']}: {job['schedule']}  [{job['id']}]")
        return

    if args.remove_all and args.profile:
        manager.remove_all(args.profile)
        return

    if args.profile:
        manager.setup_defaults(args.profile, args.poll, args.backup, args.cleanup)
        return

    parser.print_help()


if __name__ == "__main__":
    main()