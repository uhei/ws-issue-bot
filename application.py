#!/usr/bin/env python3
"""Bot listening for Webhook events from Gitlab for Issue
   and Merge Request events to add labels to issues

   Copyright 2021 Uli Heilmeier <uh@heilmeier.eu>

   SPDX-License-Identifier: GPL-3.0-or-later"""


import os
from flask import Flask
from flask import request
from flask.logging import create_logger
from dotenv import load_dotenv
import gitlab

load_dotenv()

# To check valid requests the webhook has to be configured with a secret
GITLAB_HOOK_SECRET = os.getenv('GITLAB_HOOK_SECRET') or 'DoNotUseInProduction'
# We need a access token with api scope to set labels
GITLAB_API_TOKEN = os.getenv('GITLAB_API_TOKEN')

LABEL_STATUS = 'ws-status::'
LABEL_CONFIRMED = f"{LABEL_STATUS}confirmed"
LABEL_UNCONFIRMED = f"{LABEL_STATUS}unconfirmed"
LABEL_PROGRESS = f"{LABEL_STATUS}in-progress"
LABEL_FIXED = f"{LABEL_STATUS}fixed"
LABEL_CLOSED = f"{LABEL_STATUS}closed"


application = Flask(__name__)
LOG = create_logger(application)


def get_gitlab_project(project_id):
    """Function to return a gitlab project object"""
    gitlab_token = gitlab.Gitlab(
        url='https://gitlab.com', private_token=GITLAB_API_TOKEN)
    return gitlab_token.projects.get(project_id)


def handle_issue_hook(content):
    """Function to handel incoming Issue events"""
    LOG.debug("Issue Hook: %s", content)
    try:
        attributes = content['object_attributes']
        project = get_gitlab_project(attributes['project_id'])

        # fetch the issue to add label afterwards
        editable_issue = project.issues.get(attributes['iid'])
        # handle new issues
        if attributes['action'] == "open":
            # get existing labels for this issue
            label_titles = [label['title'] for label in attributes['labels']]
            LOG.debug("labels = %s", label_titles)
            # get access level of the user who created the issue
            access_level = project.members.get(
                attributes['author_id']).access_level
            LOG.debug("access_level = %s", access_level)
            # if the user is >= Developer we expect this issue as confirmed
            if access_level >= gitlab.DEVELOPER_ACCESS:
                LOG.debug("set label %s", LABEL_CONFIRMED)
                editable_issue.labels.append(LABEL_CONFIRMED)
                editable_issue.save()
            # only set a label when there is no label set already
            elif not [title for title in label_titles if LABEL_STATUS.lower() in title.lower()]:
                LOG.debug("set label %s", LABEL_UNCONFIRMED)
                editable_issue.labels.append(LABEL_UNCONFIRMED)
                editable_issue.save()
        # handle issues which have been just closed
        if attributes['action'] == "close":
            closed_by_ref = editable_issue.closed_by()
            LOG.debug("closed by %s", closed_by_ref)
            # if the issue has been closed due to a MR
            if len(closed_by_ref) >= 1 and 'reference' in closed_by_ref[0]:
                LOG.debug("set label %s", LABEL_FIXED)
                editable_issue.labels.append(LABEL_FIXED)
                editable_issue.save()
            # reason for close is unknown, just set it closed
            else:
                LOG.debug("set label %s", LABEL_CLOSED)
                editable_issue.labels.append(LABEL_CLOSED)
                editable_issue.save()
        return "OK", 200
    except Exception as error:
        LOG.error("Unexpected error: %s", error)
        return "Something went wrong", 500


def handle_merge_request_hook(content):
    """Function to handel incoming Merge Request events"""
    LOG.debug("Merge Request Hook: %s", content)
    try:
        attributes = content['object_attributes']
        project = get_gitlab_project(attributes['target_project_id'])

        merge_request = project.mergerequests.get(attributes['iid'])
        # we only care about new MR
        if attributes['action'] == "open":
            # lookup if the MR mention some issue(s)
            closes_list = merge_request.closes_issues()
            LOG.debug("MR %s closes %s issues", attributes['iid'], closes_list.total)
            i = 0
            # set progress label for every mentioned issue
            while i < closes_list.total:
                issue = closes_list.next()
                editable_issue = project.issues.get(issue.iid)
                LOG.debug("set label %s for issue %s", LABEL_PROGRESS, issue.iid)
                editable_issue.labels.append(LABEL_PROGRESS)
                editable_issue.save()
                i += 1
        return "OK", 200
    except Exception as error:
        LOG.error("Unexpected error: %s", error)
        return "Something went wrong", 500


@application.route('/ws-hook-receiver', methods=['POST'])
def json_handler():
    """Function to handle incoming events"""
    # we expect the request to contain json data
    if not request.is_json:
        return "Bad Request", 400

    # check if the request contains the required secret
    if not ('X-Gitlab-Token' in request.headers and
            request.headers.get('X-Gitlab-Token') == GITLAB_HOOK_SECRET):
        return "Not Authorized", 401

    # we need to know the event type
    if 'X-Gitlab-Event' in request.headers:
        event = request.headers.get('X-Gitlab-Event')
    else:
        return "Bad Request", 400

    content = request.get_json()

    if event == "Issue Hook":
        return handle_issue_hook(content)
    if event == "Merge Request Hook":
        return handle_merge_request_hook(content)

    # Catch all unsupported events
    return "Event currently not supported", 501


if __name__ == "__main__":
    application.run()
