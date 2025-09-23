# JIRA Stale Issue Checker

A Python tool for intelligent analysis of JIRA issue staleness based on meaningful update history.

## Overview

This tool analyzes JIRA issues to determine when they were last meaningfully updated, filtering out noise from automated changes, comments, and other specified fields or users. Perfect for identifying truly stale issues that need attention.

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

3. **Run the script:**
   ```bash
   python jira-stale-checker.py "project = MYPROJ AND status != Done" \
     --exclude-field "Comment" \
     --exclude-user "automation-bot" \
     --before "3 months ago"
   ```

## Key Features

- **Smart filtering**: Exclude updates by field names, users, or date ranges
- **Custom field support**: Works with both field names ("Story Points") and IDs ("customfield_10001")
- **Flexible date parsing**: Supports "4 weeks ago" and "2024-01-15" formats
- **Multiple output formats**: Table, JSON, or CSV
- **Debug mode**: Detailed changelog analysis with `--debug`

## Documentation

For detailed information about the tool's architecture, usage patterns, and development guidance, see [CLAUDE.md](CLAUDE.md).

## Usage Examples

```bash
# Find issues stale for 3+ months
python jira-stale-checker.py "project = MYPROJ" --before "3 months ago"

# Recent activity excluding automation
python jira-stale-checker.py "assignee = currentUser()" \
  --exclude-user "bot" --since "2 weeks ago"

# List available fields
python jira-stale-checker.py --list-fields "dummy"
```