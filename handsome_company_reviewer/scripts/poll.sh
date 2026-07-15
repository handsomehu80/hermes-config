#!/bin/bash
# Poll assigned issues for Handsome-Review
set -e
cd /d/onboarding/handsome-s-company

# Load reviewer PAT from .env using Python (safe parsing)
ENV_FILE="/c/Users/Administrator/AppData/Local/hermes/profiles/handsome_company_reviewer/.env"
export GH_TOKEN=*** < "$ENV_FILE")
echo "GH_TOKEN loaded: ${#GH_TOKEN} chars"

echo "=== Auth check ==="
gh auth status 2>&1

echo ""
echo "=== Repo access test ==="
gh api /repos/handsome-s-company/agent_workflow 2>&1 | head -5

echo ""
echo "=== Issues assigned to Handsome-Review ==="
gh issue list --repo handsome-s-company/agent_workflow --assignee Handsome-Review --state open --json number,title,labels,assignees,createdAt,updatedAt 2>&1