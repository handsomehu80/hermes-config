#!/usr/bin/env bash
# Verify a multi-profile team is correctly set up.
# Re-run after any config change to confirm the team still works.
#
# Checks:
#   1. All expected profiles exist
#   2. Each profile has a SOUL.md
#   3. Each profile's toolset is differentiated (no two profiles have identical sets)
#   4. Kanban DB is initialized and has at least one board
#   5. Dispatcher is configured (kanban.dispatch_in_gateway)
#   6. Gateway is running
#   7. Smoke test card creates and dispatches successfully
#
# Usage: ./verify-team-setup.sh
# Exits 0 on pass, 1 on any failure.

set -uo pipefail

EXPECTED_PROFILES=(pm eng qa ast)
FAIL=0
PASS=0

echo "========================================"
echo "  Multi-Profile Team Setup Verification"
echo "========================================"
echo ""

# Check 1: profiles exist
echo "[1/7] Checking profiles exist..."
for p in "${EXPECTED_PROFILES[@]}"; do
  if hermes profile list 2>/dev/null | grep -q "^ $p\b\|^$p\b"; then
    echo "  PASS: profile '$p' exists"
    PASS=$((PASS+1))
  else
    echo "  FAIL: profile '$p' missing"
    FAIL=$((FAIL+1))
  fi
done
echo ""

# Check 2: each profile has a SOUL.md
echo "[2/7] Checking SOUL.md for each profile..."
for p in "${EXPECTED_PROFILES[@]}"; do
  SOUL="$HOME/AppData/Local/hermes/profiles/$p/SOUL.md"
  if [[ -f "$SOUL" ]]; then
    LINES=$(wc -l < "$SOUL")
    if [[ $LINES -gt 20 ]]; then
      echo "  PASS: $p/SOUL.md exists ($LINES lines)"
      PASS=$((PASS+1))
    else
      echo "  WARN: $p/SOUL.md exists but only $LINES lines (recommend >20)"
      FAIL=$((FAIL+1))
    fi
  else
    echo "  FAIL: $p/SOUL.md missing at $SOUL"
    FAIL=$((FAIL+1))
  fi
done
echo ""

# Check 3: toolset differentiation (no two profiles identical)
echo "[3/7] Checking toolset differentiation..."
declare -A TOOLSETS
for p in "${EXPECTED_PROFILES[@]}"; do
  T=$(hermes -p "$p" tools list 2>/dev/null | grep -E "✓ enabled" | awk '{print $3}' | sort | tr '\n' ',' | sed 's/,$//')
  TOOLSETS[$p]="$T"
  echo "  $p: $T"
done
# All four should be different
UNIQUE=$(printf '%s\n' "${TOOLSETS[@]}" | sort -u | wc -l)
if [[ $UNIQUE -eq 4 ]]; then
  echo "  PASS: 4 distinct toolsets"
  PASS=$((PASS+1))
elif [[ $UNIQUE -ge 3 ]]; then
  echo "  WARN: only $UNIQUE distinct toolsets (some profiles share toolset)"
else
  echo "  FAIL: only $UNIQUE distinct toolsets (profiles are not differentiated)"
  FAIL=$((FAIL+1))
fi
echo ""

# Check 4: Kanban DB initialized
echo "[4/7] Checking Kanban DB..."
KANBAN_DB="$HOME/AppData/Local/hermes/kanban.db"
if [[ -f "$KANBAN_DB" ]]; then
  echo "  PASS: $KANBAN_DB exists"
  PASS=$((PASS+1))
else
  echo "  FAIL: $KANBAN_DB not found (run: hermes kanban init)"
  FAIL=$((FAIL+1))
fi

# Check at least one board
BOARDS=$(hermes kanban boards 2>/dev/null | grep -E "●" | wc -l)
if [[ $BOARDS -ge 1 ]]; then
  echo "  PASS: $BOARDS board(s) configured"
  PASS=$((PASS+1))
else
  echo "  FAIL: no boards found"
  FAIL=$((FAIL+1))
fi
echo ""

# Check 5: dispatcher config
echo "[5/7] Checking dispatcher config..."
DISPATCH=$(grep -A2 "^kanban:" "$HOME/AppData/Local/hermes/config.yaml" 2>/dev/null | grep "dispatch_in_gateway" | awk '{print $2}')
if [[ "$DISPATCH" == "true" ]]; then
  echo "  PASS: kanban.dispatch_in_gateway = true"
  PASS=$((PASS+1))
else
  echo "  WARN: kanban.dispatch_in_gateway = $DISPATCH (set to true for embedded dispatcher)"
fi
echo ""

# Check 6: gateway running
echo "[6/7] Checking gateway..."
GW_STATUS=$(hermes gateway status 2>&1 | grep -E "running|stopped" | head -1)
if echo "$GW_STATUS" | grep -qi "running"; then
  echo "  PASS: gateway is running"
  PASS=$((PASS+1))
else
  echo "  FAIL: gateway not running ($GW_STATUS)"
  FAIL=$((FAIL+1))
fi
echo ""

# Check 7: smoke test (optional, can be skipped)
echo "[7/7] Smoke test (creates + dispatches a card)..."
SMOKE_TITLE="verify-setup-$$-$(date +%s)"
SMOKE_ID=$(hermes kanban create "$SMOKE_TITLE" \
  --assignee ast \
  --body "Verification smoke test. Just respond with 'verified'." \
  --json 2>/dev/null | jq -r .task_id 2>/dev/null)
if [[ -n "$SMOKE_ID" && "$SMOKE_ID" != "null" ]]; then
  echo "  PASS: created test card $SMOKE_ID"
  echo "  (waiting up to 120s for dispatch + completion...)"
  for i in {1..24}; do
    sleep 5
    STATUS=$(hermes kanban show "$SMOKE_ID" 2>/dev/null | grep "status:" | awk '{print $2}')
    if [[ "$STATUS" == "done" ]]; then
      echo "  PASS: card reached 'done' after ${i}*5 seconds"
      PASS=$((PASS+1))
      # Clean up
      hermes kanban archive "$SMOKE_ID" 2>/dev/null
      break
    fi
  done
  if [[ "$STATUS" != "done" ]]; then
    echo "  FAIL: card still in '$STATUS' after 120s. Dispatcher may not be running."
    FAIL=$((FAIL+1))
  fi
else
  echo "  FAIL: could not create test card"
  FAIL=$((FAIL+1))
fi
echo ""

echo "========================================"
echo "  Results: $PASS pass, $FAIL fail"
echo "========================================"
if [[ $FAIL -gt 0 ]]; then
  echo "Setup needs attention. See FAIL items above."
  exit 1
else
  echo "Team is healthy."
  exit 0
fi
