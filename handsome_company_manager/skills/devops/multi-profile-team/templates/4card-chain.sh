#!/usr/bin/env bash
# 4-card dependency chain for a feature build.
# Usage: ./4card-chain.sh "<research-topic>" "<implementation-task>" "<test-task>"
#
# Creates:
#   T1 (ast):  research
#   T2 (eng):  implement, parent=T1
#   T3 (qa):   test, parent=T2
#   T4 (pm):   report, parent=T3
#
# Verifies the chain via hermes kanban list after creation.
# Does NOT wait for completion — use `hermes kanban watch` separately.
#
# Requires: hermes CLI on PATH, jq, bash 4+

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <research-topic> <implementation-task> <test-task>"
  echo ""
  echo "Example:"
  echo "  $0 \"research FastAPI auth libs\" \"implement JWT login API\" \"write login tests\""
  exit 1
fi

RESEARCH_TOPIC="$1"
IMPL_TASK="$2"
TEST_TASK="$3"

# Verify hermes + jq are present
command -v hermes >/dev/null || { echo "ERROR: hermes not on PATH"; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq not installed"; exit 1; }

echo "Creating 4-card chain..."
echo "  T1 (ast): research: $RESEARCH_TOPIC"
echo "  T2 (eng): implement: $IMPL_TASK  [parent=T1]"
echo "  T3 (qa):  test: $TEST_TASK  [parent=T2]"
echo "  T4 (pm):  report  [parent=T3]"
echo ""

# T1: research
T1=$(hermes kanban create "research: $RESEARCH_TOPIC" \
  --assignee ast \
  --body "调研背景, 推荐方案, 给出 5 行示例代码。完成后用 kanban_complete, summary 含推荐 + 理由。" \
  --json | jq -r .task_id)

echo "  T1 = $T1 (ready)"

# T2: implement, parent=T1
T2=$(hermes kanban create "implement: $IMPL_TASK" \
  --assignee eng \
  --parent "$T1" \
  --body "基于 T1 调研结果实现。

需求:
- <功能 1>
- <功能 2>
- <功能 3>

交付:
- <主程序文件>
- <测试文件>
- 写完后用 kanban_complete, 之前先 kanban_comment 放变更文件 + 决策

T1 完成后才能开始。" \
  --json | jq -r .task_id)

echo "  T2 = $T2 (todo, parent=$T1)"

# T3: test, parent=T2
T3=$(hermes kanban create "test: $TEST_TASK" \
  --assignee qa \
  --parent "$T2" \
  --body "为 T2 实现编写测试 + 跑回归。

测试用例:
1. <正常路径>
2. <边界条件>
3. <错误处理>
4. <性能>
5. <回归>

要求:
- 用 pytest
- 覆盖率 > 70%
- 跑回归全过则 kanban_complete, 失败则创建 bug 卡 (assignee=eng)
- 先 kanban_comment 看 T2 (eng) 的 handoff

T2 完成后才能开始。" \
  --json | jq -r .task_id)

echo "  T3 = $T3 (todo, parent=$T2)"

# T4: report, parent=T3
T4=$(hermes kanban create "report: $IMPL_TASK 完成情况" \
  --assignee pm \
  --parent "$T3" \
  --body "汇总 T1/T2/T3 的结果向用户汇报。

汇报内容:
- T1 (ast) 调研推荐了哪个方案, 理由
- T2 (eng) 实现了什么, 变更文件
- T3 (qa) 测试结果 (通过/覆盖率)
- 已知限制
- 用户下一步可做什么

T3 通过后开始。" \
  --json | jq -r .task_id)

echo "  T4 = $T4 (todo, parent=$T3)"
echo ""

echo "Chain created. Cards:"
echo "  T1: $T1"
echo "  T2: $T2"
echo "  T3: $T3"
echo "  T4: $T4"
echo ""

echo "Current state:"
hermes kanban list | head -20
echo ""

echo "Watch progress with:"
echo "  hermes kanban watch"
echo "  hermes kanban tail $T1   # tail the first card to see research output"
echo ""

# Save the IDs to a file for later reference
echo "$T1 $T2 $T3 $T4" > .kanban-chain-$$.txt
echo "Card IDs saved to .kanban-chain-$$.txt"
