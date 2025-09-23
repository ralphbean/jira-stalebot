# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a JIRA stale issue analysis tool that provides intelligent filtering of JIRA issues based on their meaningful update history. The main script `jira-stale-checker.py` analyzes JIRA issue changelogs to determine when issues were last meaningfully updated, while allowing comprehensive filtering of automated/noise changes.

## Development Setup

Dependencies are managed via requirements.txt:
- `python -m pip install -r requirements.txt` - Install dependencies (jira, requests, python-dateutil)
- Main script: `jira-stale-checker.py`

## Core Functionality

The script provides sophisticated filtering capabilities:

### Authentication
- Uses JIRA personal access tokens (not basic auth)
- Configured via environment variables: `JIRA_URL` and `JIRA_TOKEN`

### Field Resolution
- Automatically maps custom field names to internal IDs
- Supports both field names ("Story Points") and field IDs ("customfield_10001")
- Built-in field mapping cache for performance

### Filtering Options
- **Field exclusions**: `--exclude-field` - Ignore updates to specific fields (comments, automated fields, etc.)
- **User exclusions**: `--exclude-user` - Ignore updates made by specific users (bots, automation)
- **Date filtering**: `--since` and `--before` for date range analysis
- **Timezone handling**: All date comparisons are timezone-aware

### Date Parsing
- Supports ISO dates: `2024-01-15`
- Supports human-friendly formats: `"4 weeks ago"`, `"2 years ago"`, `"1 month ago"`

### Output Formats
- Table (default), JSON, CSV formats
- Debug mode with detailed changelog analysis

## Key Design Decisions

### Meaningful Update Detection
The core algorithm analyzes JIRA changelog history to find the most recent "meaningful" update by:
1. Starting with issue creation date as baseline
2. Examining each changelog entry chronologically
3. Excluding changes made by specified users (`--exclude-user`)
4. Excluding changes to specified fields (`--exclude-field`)
5. Tracking the latest remaining change as "last meaningful update"

### Performance Characteristics
- Processes ALL matching issues to ensure accurate sorting (no early JIRA API limits)
- Uses changelog expansion which is API-intensive but necessary for accuracy
- Field mapping is cached per script execution
- No database persistence - pure API-based analysis

### Error Handling
- Comprehensive date parsing with clear error messages
- Field resolution warnings for unrecognized field names
- Timezone-aware datetime handling to prevent comparison errors

## Common Usage Patterns

```bash
# Find stale issues (no meaningful updates in 3 months, ignoring bot changes)
python jira-stale-checker.py "project = MYPROJ AND status != Done" \
  --exclude-field "Comment" \
  --exclude-user "automation-bot" \
  --before "3 months ago"

# Recent activity analysis (last 2 weeks, excluding sprint changes)
python jira-stale-checker.py "assignee = currentUser()" \
  --exclude-field "Sprint" \
  --since "2 weeks ago" \
  --debug
```

## Security Notes

- Never commit JIRA tokens to repository
- Use environment variables for authentication
- Personal access tokens are preferred over username/password