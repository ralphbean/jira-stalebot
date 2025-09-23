#!/usr/bin/env python3
"""
JIRA Add Comment

Simple script to add a comment to a JIRA issue.
"""

import argparse
import os
import sys

try:
    from jira import JIRA
except ImportError:
    print("Required dependencies not installed. Run: pip install jira")
    sys.exit(1)


def add_comment_to_issue(server: str, token: str, issue_key: str, comment: str):
    """
    Add a comment to a JIRA issue.

    Args:
        server: JIRA server URL
        token: JIRA personal access token
        issue_key: The issue key (e.g., "PROJ-123")
        comment: The comment text to add
    """
    try:
        # Initialize JIRA connection
        jira = JIRA(server=server, token_auth=token)

        # Get the issue (to validate it exists)
        issue = jira.issue(issue_key)

        # Add the comment
        jira.add_comment(issue, comment)

        print(f"Successfully added comment to issue {issue_key}")

    except Exception as e:
        print(f"Error adding comment to issue {issue_key}: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Add a comment to a JIRA issue')
    parser.add_argument('issue_key', help='JIRA issue key (e.g., PROJ-123)')
    parser.add_argument('comment', help='Comment text to add to the issue')
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

    add_comment_to_issue(args.url, args.token, args.issue_key, args.comment)


if __name__ == '__main__':
    main()