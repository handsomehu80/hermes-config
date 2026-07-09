#!/usr/bin/env bash
# Pilot-first workflow: skeleton + pilot data in parallel, then verify.
# Usage: ./pilot-first.sh "<skeleton-task>" "<pilot-data-task>" "<verify-task>"
#
# Creates:
#   A1 (eng): build skeleton (schema, validate script, empty files)
#   A2 (ast): fill pilot data (small subset to prove the loop)
#   A3 (qa):  verify pilot end-to-end
#
# A1 and A2 run in PARALLEL (no parent link). A3 is parent-linked to A2
# (the pilot data is the thing being verified; the skeleton is just plumbing).
#
# Does NOT wait for completion — use `hermes kanban watch` separately.
# Requires: hermes CLI on PATH, jq, bash 4+

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <skeleton-task> <pilot-data-task> <verify-task>"
  echo ""
  echo "Example:"
  echo "  $0 \\"
  echo "    \"build KB skeleton: schema + validate + empty files\" \\"
  echo "    \"fill math g1 pilot: 30-50 nodes + edges\" \\"
  echo "    \"verify math g1 pilot: schema + topo + coverage\""
  exit 1
fi

SKELETON_TASK="$1"
PILOT_TASK="$2"
VERIFY_TASK="$3"

command -v hermes >/dev/null || { echo "ERROR: hermes not on PATH"; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq not installed"; exit 1; }

echo "Creating pilot-first chain..."
echo "  A1 (eng): skeleton: $SKELETON_TASK"
echo "  A2 (ast): pilot data: $PILOT_TASK  [parallel with A1]"
echo "  A3 (qa):  verify: $VERIFY_TASK  [parent=A2]"
echo ""

# A1: skeleton (no parent — runs in parallel with A2)
A1=$(hermes kanban create "$SKELETON_TASK" \
  --assignee eng \
  --body "任务: 搭建基础结构 (数据建模任务, 不写内容)。

需交付:
- 目录结构 (按设计文档 §二)
- 顶层 schema 文件 (nodes.schema.json / edges.schema.json)
- validate 脚本 (含 schema 校验 + 拓扑 + 过滤模式)
- 1 个示例节点 (用于人类和后续 worker 理解 schema)
- README 导览

完成后用 kanban_complete (不要 kanban_block, 避免父链接陷阱), comment 报告变更文件列表 + validate 用法。

不写实际数据 — 留给 ast。" \
  --json | jq -r .task_id)

echo "  A1 = $A1 (ready, will run in parallel with A2)"

# A2: pilot data (no parent — runs in parallel with A1)
A2=$(hermes kanban create "$PILOT_TASK" \
  --assignee ast \
  --body "任务: 试点数据 (小范围内容填充, 验证 schema 跑得通)。

要求:
1. 数量限制: 30-50 节点 (不要太少也不要凑数)
2. 字段填写完整 (必填字段无缺失)
3. prerequisites 关系: 至少 80% 节点有 ≥1 个前驱
4. 完成后:
   - 跑 validate 脚本 (如果 A1 已就绪) 应通过
   - 如果 A1 还没就绪, 自己写简化版 validate, 标注待 A1 完整版本合并
   - kanban_complete + comment 报告节点数 / 边数 / 覆盖主题

试点目的: 证明 schema + validate 流程工作, 不是为了建完整内容库。" \
  --json | jq -r .task_id)

echo "  A2 = $A2 (ready, will run in parallel with A1)"

# A3: verify (parent=A2 — the pilot data is what we verify)
A3=$(hermes kanban create "$VERIFY_TASK" \
  --assignee qa \
  --parent "$A2" \
  --body "任务: 验证 A2 (ast) 的试点数据 + 端到端 validate 流程。

检查项:
1. 跑 validate 脚本所有模式, 必须通过
2. 节点数在 A2 指定的范围内
3. id 格式严格
4. 必填字段无缺失
5. 图无环 (topological sort)
6. coverage 报告: 列出覆盖 / 缺失的主题
7. 内容质量抽查 5 个节点

完成后:
- 通过: kanban_complete, comment 含 coverage 报告
- 不通过: 列具体修复点 + 创建 bug 卡 (assignee=eng)

A2 完成后才能开始 (A1 不阻塞 — skeleton 是 plumbing, 验证只关心数据 + 流程)。" \
  --json | jq -r .task_id)

echo "  A3 = $A3 (todo, parent=$A2)"
echo ""

echo "Chain created. Cards:"
echo "  A1: $A1  (ready, skeleton)"
echo "  A2: $A2  (ready, pilot data, runs parallel with A1)"
echo "  A3: $A3  (todo, verify, waits for A2)"
echo ""

echo "Current state:"
hermes kanban list | head -20
echo ""

echo "Watch progress with:"
echo "  hermes kanban watch"
echo "  hermes kanban tail $A1   # see eng writing the skeleton"
echo "  hermes kanban tail $A2   # see ast writing the pilot data"
echo ""

# Save the IDs to a file for later reference
echo "$A1 $A2 $A3" > .pilot-first-$$.txt
echo "Card IDs saved to .pilot-first-$$.txt"
