#!/usr/bin/env python3
"""
JIRA Add Label

Simple script to add a label to a JIRA issue.
"""

import argparse
import os
import sys

try:
    from jira import JIRA
except ImportError:
    print("Required dependencies not installed. Run: pip install jira")
    sys.exit(1)


def add_label_to_issue(server: str, token: str, issue_key: str, label: str):
    """
    Add a label to a JIRA issue.

    Args:
        server: JIRA server URL
        token: JIRA personal access token
        issue_key: The issue key (e.g., "PROJ-123")
        label: The label to add
    """
    try:
        # Initialize JIRA connection
        jira = JIRA(server=server, token_auth=token)

        # Get the issue
        issue = jira.issue(issue_key)

        # Get current labels
        current_labels = issue.fields.labels or []

        # Check if label already exists
        if label in current_labels:
            print(f"Label '{label}' already exists on issue {issue_key}")
            return

        # Add the new label
        new_labels = current_labels + [label]

        # Update the issue
        issue.update(fields={'labels': new_labels})

        print(f"Successfully added label '{label}' to issue {issue_key}")

    except Exception as e:
        print(f"Error adding label to issue {issue_key}: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Add a label to a JIRA issue')
    parser.add_argument('issue_key', help='JIRA issue key (e.g., PROJ-123)')
    parser.add_argument('label', help='Label to add to the issue')
    parser.add_argument('--url', help='JIRA instance URL',
                       default=os.environ.get('JIRA_URL'))
    parser.add_argument('--token', help='JIRA personal access token',
                       default=os.environ.get('JIRA_TOKEN'))

    args = parser.parse_args()

    # Validate required arguments
    if not all([args.url, args.token]):
        print("Error: JIRA URL and personal access token must be provided via arguments or environment variables")
        print("Environment variables: JIRA_URL, JIRA_TOKEN")
        sys.exit(1)

    add_label_to_issue(args.url, args.token, args.issue_key, args.label)


if __name__ == '__main__':
    main()