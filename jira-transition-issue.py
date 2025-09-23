#!/usr/bin/env python3
"""
JIRA Transition Issue

Simple script to transition a JIRA issue through a specified transition.
"""

import argparse
import os
import sys

try:
    from jira import JIRA
except ImportError:
    print("Required dependencies not installed. Run: pip install jira")
    sys.exit(1)


def transition_issue(server: str, token: str, issue_key: str, transition_name: str):
    """
    Transition a JIRA issue through a specified transition.

    Args:
        server: JIRA server URL
        token: JIRA personal access token
        issue_key: The issue key (e.g., "PROJ-123")
        transition_name: The name of the transition to execute
    """
    try:
        # Initialize JIRA connection
        jira = JIRA(server=server, token_auth=token)

        # Get the issue
        issue = jira.issue(issue_key)
        print(f"Current status of {issue_key}: {issue.fields.status.name}")

        # Get available transitions
        transitions = jira.transitions(issue)

        # Find the requested transition
        target_transition = None
        for transition in transitions:
            if transition['name'].lower() == transition_name.lower():
                target_transition = transition
                break

        if not target_transition:
            print(f"Error: Transition '{transition_name}' not available for issue {issue_key}")
            print("Available transitions:")
            for transition in transitions:
                print(f"  - {transition['name']}")
            sys.exit(1)

        # Execute the transition
        jira.transition_issue(issue, target_transition['id'])

        # Get updated issue status
        updated_issue = jira.issue(issue_key)
        print(f"Successfully transitioned {issue_key} via '{transition_name}' to: {updated_issue.fields.status.name}")

    except Exception as e:
        print(f"Error transitioning issue {issue_key}: {e}")
        sys.exit(1)


def list_transitions(server: str, token: str, issue_key: str):
    """
    List all available transitions for an issue.

    Args:
        server: JIRA server URL
        token: JIRA personal access token
        issue_key: The issue key (e.g., "PROJ-123")
    """
    try:
        # Initialize JIRA connection
        jira = JIRA(server=server, token_auth=token)

        # Get the issue
        issue = jira.issue(issue_key)
        print(f"Issue {issue_key} - Current status: {issue.fields.status.name}")

        # Get available transitions
        transitions = jira.transitions(issue)

        if not transitions:
            print("No transitions available for this issue.")
            return

        print("\nAvailable transitions:")
        for transition in transitions:
            print(f"  - {transition['name']}")

    except Exception as e:
        print(f"Error getting transitions for issue {issue_key}: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Transition a JIRA issue through a workflow transition')
    parser.add_argument('issue_key', help='JIRA issue key (e.g., PROJ-123)')
    parser.add_argument('transition_name', nargs='?', help='Name of the transition to execute')
    parser.add_argument('--url', help='JIRA instance URL',
                       default=os.environ.get('JIRA_URL'))
    parser.add_argument('--token', help='JIRA personal access token',
                       default=os.environ.get('JIRA_TOKEN'))
    parser.add_argument('--list-transitions', action='store_true',
                       help='List available transitions for the issue and exit')

    args = parser.parse_args()

    # Validate required arguments
    if not all([args.url, args.token]):
        print("Error: JIRA URL and personal access token must be provided via arguments or environment variables")
        print("Environment variables: JIRA_URL, JIRA_TOKEN")
        sys.exit(1)

    # Handle --list-transitions option
    if args.list_transitions:
        list_transitions(args.url, args.token, args.issue_key)
        return

    # Validate transition name is provided
    if not args.transition_name:
        print("Error: transition_name is required unless using --list-transitions")
        parser.print_help()
        sys.exit(1)

    transition_issue(args.url, args.token, args.issue_key, args.transition_name)


if __name__ == '__main__':
    main()