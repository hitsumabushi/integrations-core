# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import requests

from .constants import CHANGELOG_LABEL_PREFIX

API_URL = 'https://api.github.com'
PR_ENDPOINT = API_URL + '/repos/DataDog/{}/pulls/{}'
DEFAULT_REPO = 'integrations-core'
PR_PATTERN = re.compile(r'\(#(\d+)\)')  # match something like `(#1234)` and return `1234` in a group


def get_auth_info(config=None):
    """
    See if a personal access token was passed
    """
    gh_config = (config or {}).get('github', {})
    user = gh_config.get('user') or os.getenv('DD_GITHUB_USER')
    token = gh_config.get('token') or os.getenv('DD_GITHUB_TOKEN')
    if user and token:
        return user, token


def get_pr_labels(pr_payload):
    labels = []
    for label in (pr_payload.get('labels') or []):
        name = label.get('name')
        if name:
            labels.append(name)

    return labels


def get_pr_milestone(pr_payload):
    return (pr_payload.get('milestone') or {}).get('title', '')


def get_changelog_types(pr_payload):
    """
    Fetch the labels from the PR and process the ones related to the changelog.
    """
    changelog_labels = []
    for name in get_pr_labels(pr_payload):
        if name.startswith(CHANGELOG_LABEL_PREFIX):
            # only add the name, e.g. for `changelog/Added` it's just `Added`
            changelog_labels.append(name.split(CHANGELOG_LABEL_PREFIX)[1])

    return changelog_labels


def get_pr(pr_num, config=None, repo=DEFAULT_REPO, raw=False):
    """
    Get the payload for the given PR number. Let exceptions bubble up.
    """
    response = requests.get(
        PR_ENDPOINT.format(repo, pr_num),
        auth=get_auth_info(config)
    )

    if raw:
        return response
    else:
        response.raise_for_status()
        return response.json()


def get_pr_from_hash(commit_hash, repo, config=None, raw=False):
    response = requests.get(
        'https://api.github.com/search/issues?q=sha:{}+repo:DataDog/{}'.format(
            commit_hash, repo
        ),
        auth=get_auth_info(config)
    )

    if raw:
        return response
    else:
        response.raise_for_status()
        return response.json()


def from_contributor(pr_payload):
    """
    If the PR comes from a fork, we can safely assumed it's from an
    external contributor.
    """
    try:
        return pr_payload.get('head', {}).get('repo', {}).get('fork') is True
    except Exception:
        return False


def parse_pr_number(log_line):
    match = re.search(PR_PATTERN, log_line)
    if match:
        return match.group(1)


def parse_pr_numbers(git_log_lines):
    """
    Parse PR numbers from commit messages. At GitHub those have the format:

        `here is the message (#1234)`

    being `1234` the PR number.
    """
    prs = []
    for line in git_log_lines:
        pr_number = parse_pr_number(line)
        if pr_number:
            prs.append(pr_number)
    return prs
