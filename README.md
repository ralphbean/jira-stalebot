# JIRA Stale Issue Management

A suite of Python tools for intelligent JIRA stale issue management - from identification to automated cleanup.

## Overview

This toolkit provides four complementary scripts for managing stale JIRA issues:

1. **`jira-stale-checker.py`** - Analyzes issues to identify staleness based on meaningful update history
2. **`jira-add-label.py`** - Adds labels to issues (e.g., marking them as "stale")
3. **`jira-add-comment.py`** - Adds comments to issues (e.g., stale notifications)
4. **`jira-transition-issue.py`** - Transitions issues through workflow states (e.g., closing stale issues)

Together, these tools enable a complete stale issue management workflow: identify → label → notify → monitor → close.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export JIRA_URL="https://yourcompany.atlassian.net"
   export JIRA_TOKEN="your_personal_access_token"
   ```

3. **Run a complete stale issue workflow:**
   ```bash
   # 1. Identify stale issues
   python jira-stale-checker.py "project = MYPROJ AND status != Done" \
     --exclude-field "Comment" \
     --exclude-user "automation-bot" \
     --before "3 months ago" \
     --format json > stale_issues.json

   # 2. Label them as stale and notify stakeholders
   for issue in $(jq -r '.[].key' stale_issues.json); do
     python jira-add-label.py "$issue" "stale"
     python jira-add-comment.py "$issue" "This issue has been labeled as stale due to 3+ months of inactivity. Please update if still relevant."
   done

   # 3. Later, close issues that still have the stale label
   python jira-stale-checker.py "project = MYPROJ AND labels = stale" \
     --before "2 weeks ago" --format json | \
   jq -r '.[].key' | \
   while read issue; do
     python jira-transition-issue.py "$issue" "Close Issue"
   done
   ```

## Key Features

- **Intelligent stale detection**: Exclude updates by field names, users, or date ranges
- **Custom field support**: Works with both field names ("Story Points") and IDs ("customfield_10001")
- **Flexible date parsing**: Supports "4 weeks ago" and "2024-01-15" formats
- **Multiple output formats**: Table, JSON, or CSV for easy scripting
- **Complete workflow**: From identification to automated cleanup
- **Safe operations**: Idempotent labeling and transition validation

## Documentation

For detailed information about the tool's architecture, usage patterns, and development guidance, see [CLAUDE.md](CLAUDE.md).

## Individual Script Usage

```bash
# Stale issue analysis
python jira-stale-checker.py "project = MYPROJ" --before "3 months ago"
python jira-stale-checker.py --list-fields "dummy"

# Issue labeling
python jira-add-label.py PROJ-123 "stale"
python jira-add-label.py PROJ-456 "needs-review"

# Issue commenting
python jira-add-comment.py PROJ-123 "This issue appears to be stale."
python jira-add-comment.py PROJ-456 "Please update if still relevant."

# Issue transitions
python jira-transition-issue.py PROJ-123 "Close Issue"
python jira-transition-issue.py PROJ-123 --list-transitions
```

## Workflow Examples

```bash
# Two-phase stale cleanup with grace period
# Phase 1: Label stale issues and notify (6+ months inactive)
python jira-stale-checker.py "project = MYPROJ AND status != Done" \
  --before "6 months ago" --format json | \
jq -r '.[].key' | \
while read issue; do
  python jira-add-label.py "$issue" "stale"
  python jira-add-comment.py "$issue" "This issue has been automatically labeled as stale due to 6+ months of inactivity. If still relevant, please update within 2 weeks or it will be closed."
done

# Phase 2: Close issues still stale after 2 weeks grace period
python jira-stale-checker.py "project = MYPROJ AND labels = stale" \
  --before "2 weeks ago" --format json | \
jq -r '.[].key' | \
while read issue; do
  python jira-transition-issue.py "$issue" "Close Issue"
done
```