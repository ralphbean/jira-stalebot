# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a JIRA stale issue management toolkit consisting of four complementary scripts:

1. **`jira-stale-checker.py`** - Analyzes issue changelogs to identify staleness based on meaningful update history
2. **`jira-add-label.py`** - Simple utility to add labels to JIRA issues
3. **`jira-add-comment.py`** - Simple utility to add comments to JIRA issues
4. **`jira-transition-issue.py`** - Transitions issues through workflow states

The toolkit enables a complete stale issue management workflow: identify stale issues → label them → notify stakeholders → provide grace period → close unaddressed issues.

## Development Setup

Dependencies are managed via requirements.txt:
- `python -m pip install -r requirements.txt` - Install dependencies (jira, requests, python-dateutil)
- All scripts use the same authentication pattern and environment variables
- Scripts: `jira-stale-checker.py`, `jira-add-label.py`, `jira-add-comment.py`, `jira-transition-issue.py`

## Core Functionality

### jira-stale-checker.py
The main analysis tool provides sophisticated filtering capabilities:

### Authentication
- Uses JIRA personal access tokens (not basic auth)
- Configured via environment variables: `JIRA_URL` and `JIRA_TOKEN`

### Field Resolution
- Uses field names directly as they appear in JIRA changelog entries
- Supports field names like "Story Points", "Comment", "Sprint", etc.
- Simplified approach without internal ID mapping for better reliability

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

### jira-add-label.py
Simple utility for adding labels to issues:
- Idempotent operation (won't add duplicate labels)
- Preserves existing labels
- Clear success/failure feedback
- Same authentication pattern as other scripts

### jira-add-comment.py
Simple utility for adding comments to issues:
- Validates issue exists before adding comment
- Supports multi-line comments
- Clear success/failure feedback
- Same authentication pattern as other scripts

### jira-transition-issue.py
Workflow transition management:
- Case-insensitive transition name matching
- Validation of available transitions
- Before/after status reporting
- Discovery mode with `--list-transitions`
- Handles workflow complexity gracefully

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
- Direct field name matching without caching overhead
- No database persistence - pure API-based analysis

### Error Handling
- Comprehensive date parsing with clear error messages
- Direct field name matching reduces field resolution complexity
- Timezone-aware datetime handling to prevent comparison errors

## Common Usage Patterns

### Individual Script Usage
```bash
# Stale issue analysis
python jira-stale-checker.py "project = MYPROJ AND status != Done" \
  --exclude-field "Comment" \
  --exclude-user "automation-bot" \
  --before "3 months ago"

# Issue labeling
python jira-add-label.py PROJ-123 "stale"

# Issue commenting
python jira-add-comment.py PROJ-123 "This issue appears to be stale."

# Issue transitions
python jira-transition-issue.py PROJ-123 "Close Issue"
python jira-transition-issue.py PROJ-123 --list-transitions
```

### Complete Stale Issue Management Workflow
```bash
# Phase 1: Identify and label stale issues (6+ months without meaningful updates)
python jira-stale-checker.py "project = MYPROJ AND status != Done" \
  --exclude-field "Comment" \
  --exclude-field "Work Log" \
  --exclude-user "automation-bot" \
  --before "6 months ago" \
  --format json | \
jq -r '.[].key' | \
while read issue; do
  echo "Labeling $issue as stale..."
  python jira-add-label.py "$issue" "stale"
  python jira-add-comment.py "$issue" "This issue has been automatically labeled as stale due to 6+ months of inactivity. If still relevant, please update within 2-4 weeks or it will be closed."
done

# Phase 2: Grace period - notify teams, send reports, etc.
# (Allow 2-4 weeks for teams to respond to stale labels)

# Phase 3: Close issues that remain stale after grace period
python jira-stale-checker.py "project = MYPROJ AND labels = stale" \
  --before "2 weeks ago" \
  --format json | \
jq -r '.[].key' | \
while read issue; do
  echo "Closing stale issue $issue..."
  python jira-transition-issue.py "$issue" "Close Issue"
done
```

### Advanced Filtering Examples
```bash
# Find issues stale despite recent comments (exclude only automation)
python jira-stale-checker.py "project = MYPROJ" \
  --exclude-user "jenkins" \
  --exclude-user "github-bot" \
  --before "3 months ago"

# Identify issues with recent automation but no human activity
python jira-stale-checker.py "project = MYPROJ" \
  --exclude-field "Comment" \
  --exclude-field "Attachment" \
  --exclude-user "automation-bot" \
  --exclude-user "ci-system" \
  --before "1 month ago" \
  --debug
```

## Security Notes

- Never commit JIRA tokens to repository
- Use environment variables for authentication
- Personal access tokens are preferred over username/password