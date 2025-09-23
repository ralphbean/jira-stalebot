#!/usr/bin/env python3
"""
JIRA Stale Issue Checker

Queries JIRA using JQL and sorts issues by their most recent update date,
excluding updates to specified fields from consideration.
"""

import argparse
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

# Global debug flag
DEBUG = False

def debug_print(message: str):
    """Print debug message to stderr if debug mode is enabled."""
    if DEBUG:
        print(f"DEBUG: {message}", file=sys.stderr)

try:
    from jira import JIRA
    import requests
    from dateutil import parser as date_parser
    from dateutil.relativedelta import relativedelta
    import re
except ImportError:
    print("Required dependencies not installed. Run: pip install jira requests python-dateutil")
    sys.exit(1)


class JiraStaleChecker:
    def __init__(self, server: str, token: str):
        """Initialize JIRA connection using personal access token."""
        self.jira = JIRA(server=server, token_auth=token)
        self._field_mapping = None  # Cache for field name to ID mapping

    def get_issues_with_history(self, jql: str, exclude_fields: List[str], exclude_users: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get issues matching JQL and calculate their last meaningful update date.

        Args:
            jql: JQL query string
            exclude_fields: List of field names to exclude from update consideration
            exclude_users: List of usernames to exclude from update consideration

        Returns:
            List of dictionaries with issue data and calculated last update date
        """
        debug_print(f"Executing JQL query: {jql}")

        # Resolve field names to proper identifiers
        resolved_exclude_fields = self._resolve_field_identifiers(exclude_fields)
        exclude_users = exclude_users or []

        # Get issues from JQL query
        debug_print("Fetching issues from JIRA...")
        issues = self.jira.search_issues(jql, expand='changelog', maxResults=False)
        debug_print(f"Found {len(issues)} issues matching JQL query")

        results = []

        for i, issue in enumerate(issues, 1):
            debug_print(f"Processing issue {i}/{len(issues)}: {issue.key}")
            last_meaningful_update = self._get_last_meaningful_update(issue, resolved_exclude_fields, exclude_users)

            results.append({
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'created': issue.fields.created,
                'updated': issue.fields.updated,
                'last_meaningful_update': last_meaningful_update,
                'url': f"{self.jira.server_url}/browse/{issue.key}"
            })

        # Sort by last meaningful update date (most recent first)
        debug_print("Sorting issues by last meaningful update date...")
        results.sort(key=lambda x: x['last_meaningful_update'], reverse=True)
        debug_print(f"Processing complete. Returning {len(results)} issues.")

        return results

    def _get_last_meaningful_update(self, issue, exclude_fields: List[str], exclude_users: List[str] = None) -> str:
        """
        Find the most recent update to an issue, excluding specified fields and users.

        Args:
            issue: JIRA issue object
            exclude_fields: List of field names to exclude
            exclude_users: List of usernames to exclude

        Returns:
            ISO date string of last meaningful update
        """
        exclude_users = exclude_users or []

        # Start with issue creation date as baseline
        last_update = datetime.fromisoformat(issue.fields.created.replace('Z', '+00:00'))
        debug_print(f"  Issue {issue.key} created: {last_update.isoformat()}")

        meaningful_updates_count = 0
        excluded_updates_count = 0
        excluded_user_updates_count = 0

        # Check changelog for meaningful updates
        if hasattr(issue, 'changelog') and issue.changelog:
            debug_print(f"  Analyzing {len(issue.changelog.histories)} changelog entries...")
            for history in issue.changelog.histories:
                # Get the author of this change
                change_author = history.author.name if hasattr(history.author, 'name') else str(history.author)

                # Skip if this user should be excluded
                if change_author in exclude_users:
                    debug_print(f"    {history.created}: Excluding change by user '{change_author}'")
                    excluded_user_updates_count += 1
                    continue

                # Check if this history entry contains meaningful changes
                has_meaningful_change = False
                meaningful_fields = []
                excluded_fields_in_history = []

                for item in history.items:
                    # Skip if this field should be excluded
                    if item.field not in exclude_fields:
                        has_meaningful_change = True
                        meaningful_fields.append(item.field)
                    else:
                        excluded_fields_in_history.append(item.field)

                if excluded_fields_in_history:
                    debug_print(f"    {history.created}: Excluded fields changed: {excluded_fields_in_history} (by {change_author})")
                    excluded_updates_count += 1

                if has_meaningful_change:
                    meaningful_updates_count += 1
                    history_date = datetime.fromisoformat(history.created.replace('Z', '+00:00'))
                    debug_print(f"    {history.created}: Meaningful change in fields: {meaningful_fields} (by {change_author})")
                    if history_date > last_update:
                        last_update = history_date
                        debug_print(f"    → New last meaningful update: {last_update.isoformat()}")

        debug_print(f"  Summary for {issue.key}: {meaningful_updates_count} meaningful updates, {excluded_updates_count} excluded field updates, {excluded_user_updates_count} excluded user updates")
        debug_print(f"  Final last meaningful update: {last_update.isoformat()}")

        return last_update.isoformat()

    def _get_field_mapping(self) -> Dict[str, str]:
        """
        Get mapping of field names to field IDs.

        Returns:
            Dictionary mapping field names (and aliases) to field IDs
        """
        if self._field_mapping is not None:
            debug_print("Using cached field mapping")
            return self._field_mapping

        debug_print("Fetching field mapping from JIRA API...")
        self._field_mapping = {}

        try:
            # Get all fields from JIRA
            fields = self.jira.fields()
            debug_print(f"Retrieved {len(fields)} fields from JIRA")

            custom_field_count = 0
            for field in fields:
                field_id = field['id']
                field_name = field['name']

                # Map both the exact name and lowercased version
                self._field_mapping[field_name] = field_id
                self._field_mapping[field_name.lower()] = field_id

                # For custom fields, also map by ID (in case user provides the ID directly)
                if field_id.startswith('customfield_'):
                    self._field_mapping[field_id] = field_id
                    custom_field_count += 1

            debug_print(f"Mapped {len(fields)} total fields ({custom_field_count} custom fields)")

        except Exception as e:
            print(f"Warning: Could not fetch field mapping: {e}")
            self._field_mapping = {}

        return self._field_mapping

    def _resolve_field_identifiers(self, exclude_fields: List[str]) -> List[str]:
        """
        Convert user-provided field names to the identifiers used in changelog.

        Args:
            exclude_fields: List of field names provided by user

        Returns:
            List of field identifiers that can be compared against changelog items
        """
        debug_print(f"Resolving {len(exclude_fields)} field identifiers: {exclude_fields}")
        field_mapping = self._get_field_mapping()
        resolved_fields = []
        invalid_fields = []

        for field in exclude_fields:
            debug_print(f"  Resolving field: '{field}'")
            # Try exact match first
            if field in field_mapping:
                resolved_id = field_mapping[field]
                resolved_fields.append(resolved_id)
                debug_print(f"    → Exact match: {resolved_id}")
            # Try case-insensitive match
            elif field.lower() in field_mapping:
                resolved_id = field_mapping[field.lower()]
                resolved_fields.append(resolved_id)
                debug_print(f"    → Case-insensitive match: {resolved_id}")
            # If it's already a field ID, keep it as-is
            elif field.startswith('customfield_'):
                resolved_fields.append(field)
                debug_print(f"    → Already a field ID: {field}")
            # Try to match standard field names (case-insensitive)
            else:
                # Some common field mappings for standard fields
                standard_fields = {
                    'summary': 'summary',
                    'description': 'description',
                    'status': 'status',
                    'assignee': 'assignee',
                    'reporter': 'reporter',
                    'priority': 'priority',
                    'resolution': 'resolution',
                    'labels': 'labels',
                    'comment': 'comment',
                    'attachment': 'attachment',
                    'worklog': 'worklog',
                    'work log': 'worklog',
                    'link': 'issuelinks'
                }

                field_lower = field.lower()
                if field_lower in standard_fields:
                    resolved_fields.append(standard_fields[field_lower])
                    debug_print(f"    → Standard field match: {standard_fields[field_lower]}")
                else:
                    invalid_fields.append(field)
                    debug_print(f"    → No match found for: {field}")

        if invalid_fields:
            print(f"Warning: Could not resolve the following fields: {', '.join(invalid_fields)}")
            print("Available custom fields can be listed by examining JIRA field configuration")

        debug_print(f"Final resolved fields: {resolved_fields}")
        return resolved_fields


def parse_since_date(since_str: str) -> datetime:
    """
    Parse a date string in either YYYY-MM-DD format or human-friendly format.

    Args:
        since_str: Date string like "2024-01-15" or "4 weeks ago"

    Returns:
        datetime object representing the parsed date

    Raises:
        ValueError: If the date string cannot be parsed
    """
    if not since_str:
        raise ValueError("Empty date string")

    # Try ISO date format first (YYYY-MM-DD)
    try:
        parsed_date = datetime.fromisoformat(since_str)
        # If the parsed date is naive, make it timezone-aware (UTC)
        if parsed_date.tzinfo is None:
            from datetime import timezone
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        return parsed_date
    except ValueError:
        pass

    # Try human-friendly relative dates
    # Use UTC timezone to match JIRA timestamps
    from datetime import timezone
    now = datetime.now(timezone.utc)
    since_str_lower = since_str.lower().strip()

    # Pattern matching for relative dates
    patterns = [
        # "4 weeks ago", "2 years ago", "1 month ago"
        (r'^(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago$', 1),
        # "a week ago", "an hour ago"
        (r'^(a|an)\s+(second|minute|hour|day|week|month|year)\s+ago$', 1),
    ]

    for pattern, multiplier in patterns:
        match = re.match(pattern, since_str_lower)
        if match:
            if match.group(1) in ['a', 'an']:
                amount = 1
                unit = match.group(2)
            else:
                amount = int(match.group(1))
                unit = match.group(2)

            # Convert to relativedelta arguments
            if unit.startswith('second'):
                delta = relativedelta(seconds=amount)
            elif unit.startswith('minute'):
                delta = relativedelta(minutes=amount)
            elif unit.startswith('hour'):
                delta = relativedelta(hours=amount)
            elif unit.startswith('day'):
                delta = relativedelta(days=amount)
            elif unit.startswith('week'):
                delta = relativedelta(weeks=amount)
            elif unit.startswith('month'):
                delta = relativedelta(months=amount)
            elif unit.startswith('year'):
                delta = relativedelta(years=amount)
            else:
                raise ValueError(f"Unknown time unit: {unit}")

            return now - delta

    # Try dateutil's parser as fallback
    try:
        parsed_date = date_parser.parse(since_str)
        # If the parsed date is naive, make it timezone-aware (UTC)
        if parsed_date.tzinfo is None:
            from datetime import timezone
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        return parsed_date
    except Exception as e:
        raise ValueError(f"Could not parse date '{since_str}'. Use formats like 'YYYY-MM-DD', '4 weeks ago', or '2 years ago'. Error: {e}")


def filter_issues_by_date_range(issues: List[Dict[str, Any]], since_date: datetime = None, before_date: datetime = None) -> List[Dict[str, Any]]:
    """
    Filter issues to only include those updated within the given date range.

    Args:
        issues: List of issue dictionaries
        since_date: Only include issues updated on or after this date (optional)
        before_date: Only include issues updated on or before this date (optional)

    Returns:
        Filtered list of issues
    """
    if not since_date and not before_date:
        return issues

    filtered_issues = []

    for issue in issues:
        issue_last_update = datetime.fromisoformat(issue['last_meaningful_update'])
        include_issue = True
        exclusion_reason = None

        # Check since date constraint
        if since_date and issue_last_update < since_date:
            include_issue = False
            exclusion_reason = f"last update {issue_last_update.isoformat()} is before --since date {since_date.isoformat()}"

        # Check before date constraint
        if before_date and issue_last_update > before_date:
            include_issue = False
            exclusion_reason = f"last update {issue_last_update.isoformat()} is after --before date {before_date.isoformat()}"

        if include_issue:
            filtered_issues.append(issue)
        else:
            debug_print(f"  Excluding {issue['key']}: {exclusion_reason}")

    filter_description = []
    if since_date:
        filter_description.append(f"--since {since_date.isoformat()}")
    if before_date:
        filter_description.append(f"--before {before_date.isoformat()}")

    debug_print(f"Filtered {len(issues)} issues down to {len(filtered_issues)} based on {' and '.join(filter_description)} filter(s)")
    return filtered_issues


def main():
    parser = argparse.ArgumentParser(description='Find JIRA issues sorted by last meaningful update')
    parser.add_argument('jql', help='JQL query to find issues')
    parser.add_argument('--url', help='JIRA instance URL',
                       default=os.environ.get('JIRA_URL'))
    parser.add_argument('--token', help='JIRA personal access token',
                       default=os.environ.get('JIRA_TOKEN'))
    parser.add_argument('--exclude-field', action='append', dest='exclude_fields',
                       help='Field to exclude from update consideration. Can be field name (e.g., "Story Points") or field ID (e.g., "customfield_10001"). Can be used multiple times.')
    parser.add_argument('--format', choices=['json', 'table', 'csv'], default='table',
                       help='Output format')
    parser.add_argument('--list-fields', action='store_true',
                       help='List available fields and their IDs, then exit')
    parser.add_argument('--since', help='Only include issues with meaningful updates since this date. Accepts YYYY-MM-DD format or human-friendly formats like "4 weeks ago", "2 years ago"')
    parser.add_argument('--before', help='Only include issues with meaningful updates before this date. Accepts YYYY-MM-DD format or human-friendly formats like "4 weeks ago", "2 years ago"')
    parser.add_argument('--exclude-user', action='append', dest='exclude_users',
                       help='Username to exclude from update consideration. Changes made by this user will be ignored when determining last meaningful update. Can be used multiple times.')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output to stderr')

    args = parser.parse_args()

    # Validate required arguments
    if not all([args.url, args.token]):
        print("Error: JIRA URL and personal access token must be provided via arguments or environment variables")
        print("Environment variables: JIRA_URL, JIRA_TOKEN")
        sys.exit(1)

    # Set global debug flag
    global DEBUG
    DEBUG = args.debug

    try:
        debug_print("Initializing JIRA connection...")
        checker = JiraStaleChecker(args.url, args.token)
        debug_print("JIRA connection established")

        # Handle --list-fields option
        if args.list_fields:
            debug_print("Listing available fields...")
            _list_available_fields(checker)
            sys.exit(0)

        exclude_fields = args.exclude_fields or []
        exclude_users = args.exclude_users or []
        debug_print(f"Starting issue analysis with {len(exclude_fields)} excluded fields and {len(exclude_users)} excluded users")
        if exclude_users:
            debug_print(f"Excluded users: {exclude_users}")
        issues = checker.get_issues_with_history(args.jql, exclude_fields, exclude_users)

        # Apply --since and --before filters if provided
        since_date = None
        before_date = None

        if args.since:
            try:
                since_date = parse_since_date(args.since)
                debug_print(f"Applying --since filter: {since_date.isoformat()}")
            except ValueError as e:
                print(f"Error parsing --since date: {e}")
                sys.exit(1)

        if args.before:
            try:
                before_date = parse_since_date(args.before)
                debug_print(f"Applying --before filter: {before_date.isoformat()}")
            except ValueError as e:
                print(f"Error parsing --before date: {e}")
                sys.exit(1)

        # Apply date range filtering
        if since_date or before_date:
            issues = filter_issues_by_date_range(issues, since_date, before_date)

        # Output results
        debug_print(f"Outputting {len(issues)} issues in {args.format} format")
        if args.format == 'json':
            print(json.dumps(issues, indent=2))
        elif args.format == 'csv':
            _output_csv(issues)
        else:
            _output_table(issues)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def _output_table(issues: List[Dict[str, Any]]):
    """Output issues in table format."""
    if not issues:
        print("No issues found.")
        return

    # Print header
    print(f"{'Key':<12} {'Status':<15} {'Last Meaningful Update':<25} {'Summary':<50}")
    print("-" * 102)

    # Print issues
    for issue in issues:
        last_update = datetime.fromisoformat(issue['last_meaningful_update']).strftime('%Y-%m-%d %H:%M:%S')
        summary = issue['summary'][:47] + "..." if len(issue['summary']) > 50 else issue['summary']
        print(f"{issue['key']:<12} {issue['status']:<15} {last_update:<25} {summary}")


def _output_csv(issues: List[Dict[str, Any]]):
    """Output issues in CSV format."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['key', 'summary', 'status', 'assignee', 'created', 'updated', 'last_meaningful_update', 'url'])
    writer.writeheader()
    writer.writerows(issues)
    print(output.getvalue())


def _list_available_fields(checker: JiraStaleChecker):
    """List all available fields and their IDs."""
    try:
        field_mapping = checker._get_field_mapping()
        if not field_mapping:
            print("No fields found or unable to fetch field information.")
            return

        # Group fields by type
        standard_fields = []
        custom_fields = []

        # Get unique field entries (avoid duplicates from case-insensitive mapping)
        seen_ids = set()
        for name, field_id in field_mapping.items():
            if field_id in seen_ids:
                continue
            seen_ids.add(field_id)

            if field_id.startswith('customfield_'):
                custom_fields.append((name, field_id))
            else:
                standard_fields.append((name, field_id))

        print("Available JIRA Fields:")
        print("=" * 50)

        if standard_fields:
            print("\nStandard Fields:")
            print("-" * 30)
            for name, field_id in sorted(standard_fields):
                if name.lower() != name:  # Only show the properly cased version
                    print(f"  {name:<25} ({field_id})")

        if custom_fields:
            print(f"\nCustom Fields ({len(custom_fields)} total):")
            print("-" * 30)
            for name, field_id in sorted(custom_fields):
                if name.lower() != name:  # Only show the properly cased version
                    print(f"  {name:<25} ({field_id})")

        print(f"\nUsage examples:")
        print(f"  --exclude-field \"Comment\"")
        print(f"  --exclude-field \"Story Points\"")
        print(f"  --exclude-field \"customfield_10001\"")
        print(f"  --exclude-user \"automation-bot\"")
        print(f"\nNote: All matching issues will be processed and returned.")
        print(f"Use more specific JQL queries to reduce the result set if needed.")

    except Exception as e:
        print(f"Error listing fields: {e}")


if __name__ == '__main__':
    main()