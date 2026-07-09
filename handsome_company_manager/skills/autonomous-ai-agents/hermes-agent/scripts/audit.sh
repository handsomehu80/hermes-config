#!/bin/bash
# hermes-setup-audit companion script
# Runs the 4-command diagnostic combo in parallel and prints a brief summary.
# Use when user asks to check / audit / optimize Hermes configuration.
#
# Usage:  bash scripts/audit.sh
#         hermes doctor | tail -60  (if you only want one piece)

set -e

echo "========================================"
echo "  Hermes Agent Setup Audit"
echo "  $(date)"
echo "========================================"
echo

# Run all 4 in parallel
hermes doctor > /tmp/hermes_doctor.txt 2>&1 &
hermes status --all > /tmp/hermes_status.txt 2>&1 &
hermes config check > /tmp/hermes_config_check.txt 2>&1 &
hermes tools list > /tmp/hermes_tools.txt 2>&1 &

wait

echo "=========================================="
echo " 1) hermes doctor (health + tool availability)"
echo "=========================================="
cat /tmp/hermes_doctor.txt
echo

echo "=========================================="
echo " 2) hermes status --all (components + auth)"
echo "=========================================="
cat /tmp/hermes_status.txt
echo

echo "=========================================="
echo " 3) hermes config check (env var gaps)"
echo "=========================================="
cat /tmp/hermes_config_check.txt
echo

echo "=========================================="
echo " 4) hermes tools list (toolset enablement)"
echo "=========================================="
cat /tmp/hermes_tools.txt
echo

# Quick roll-up
echo "=========================================="
echo "  Summary"
echo "=========================================="
DOC_WARN=$(grep -c "⚠" /tmp/hermes_doctor.txt || true)
DOC_OK=$(grep -c "✓" /tmp/hermes_doctor.txt || true)
echo "  doctor:          $DOC_OK ok, $DOC_WARN warning(s)"
TOOL_OK=$(grep -c "✓ enabled" /tmp/hermes_tools.txt || true)
TOOL_OFF=$(grep -c "✗ disabled" /tmp/hermes_tools.txt || true)
echo "  toolsets:        $TOOL_OK enabled, $TOOL_OFF disabled"
echo
echo "  Full outputs saved to /tmp/hermes_*.txt for diffing across runs."
