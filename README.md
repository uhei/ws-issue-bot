# ws-issue-bot

### Description

ws-issue-bot is a Python script using [Flask](https://palletsprojects.com/p/flask/) and [python-gitlab](https://github.com/python-gitlab/python-gitlab) to set [scoped labels](https://docs.gitlab.com/ee/user/project/labels.html#scoped-labels) on Gitlab Issues. Target project for this bot is [https://gitlab.com/wireshark/wireshark](https://gitlab.com/wireshark/wireshark)

This is done by listing for [Issue](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#issue-events) and [Merge Requests Webhooks](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#merge-request-events).

When there is a new issue and the user is a member of group Developer or Maintainer or Owner the label ws-status::confirmed is set. Otherwise when there is no ws-status:: label the label ws-status::unconfirmed is set.

When there is a new Merge Request which mentions an issue, the bot set label ws-status::in-progress for this issue.

When a issue is closed and it was closed by a MR label ws-status::fixed is set. Otherwise label ws-status::closed is set.

The label ws-status::waiting-for-response can't be automated. Therefore it has to be set manually.

### How to run it


* An API token with API permissions for the project is needed (would make sense to use a dedicated user for this).
* A platform running a WSGI/Reverse proxy stack (for example nginx and gunicorn or AWS Elastic Beanstalk).
* The environment variables GITLAB_HOOK_SECRET and GITLAB_API_TOKEN have to be set to run the bot.
* Configured Issues and Merge request event Webhooks in the project settings menu. A secret token must be set.
