# Shakira Architecture Overview

Shakira is Duolingo's shake-to-report bug reporting system that enables users to report issues by shaking their mobile devices.

## System Overview

```
Mobile Apps → API Gateway → Processing Pipeline → JIRA/Slack
     ↓              ↓               ↓                 ↓
   Shake       Issue Data       AI Analysis       Bug Tickets
  Gesture      Collection       & Routing         & Channels
```

## How It Works

1. **Data Collection**: User shakes device or submits web form, screenshot + metadata captured

   - Web interface: [`ShakeToReportForm.tsx`](../web/src/components/ShakeToReportForm.tsx)
   - API endpoints: [`api.py`](../jeeves/view/api.py) - `report_issue()` functions

2. **AI Processing**: GPT analyzes for priority and feature detection

   - Main orchestrator: [`shakira.py`](../jeeves/manager/shakira.py) - `ShakiraManager.report_issue()`
   - Feature suggestions: [`shakira.py`](../jeeves/manager/shakira.py) - `suggest_features()`

3. **Duplicate Detection**: Intelligent linking against existing tickets

   - Duplicate detection: [`shakira.py`](../jeeves/manager/shakira.py) - `detect_duplicates()`
   - Graph management: [`api.py`](../jeeves/view/api.py) - `fully_connect_duplicates()`

4. **Routing**: Creates JIRA tickets (DLAI/iOS, DLAA/Android, DLAW/Web) and/or Slack notifications

   - JIRA integration: [`shakira_jira.py`](../jeeves/manager/shakira_jira.py) - `ShakiraJiraApiClient`
   - Slack integration: [`shakira_slack.py`](../jeeves/manager/shakira_slack.py) - `ShakiraSlackApiClient`

5. **Automation**: Features auto-created on deployment, weekly digest emails sent
   - Feature creation: [`create_jira_features.py`](../jeeves/scripts/shakira/create_jira_features.py) - Jenkins CI/CD on every production deploy
   - Email digests: [`send_bug_digest_emails.py`](../jeeves/scripts/shakira/send_bug_digest_emails.py) - AWS ECS scheduled task, Mondays 4:00 PM UTC
   - Feature config: [`jira_features.py`](../jeeves/config/jira_features.py) - `JIRA_FEATURES`

## Infrastructure

- **Main API**: AWS ECS service (`duolingo-jeeves-internal`)
- **Email Automation**: [ECS scheduled task](https://us-east-1.console.aws.amazon.com/ecs/v2/task-definitions/duolingo-jeeves-email-sender-prod?status=ACTIVE&region=us-east-1) (`duolingo-jeeves-email-sender`) with cron schedule
- **Feature Automation**: Jenkins pipeline runs during production deployments

## References

- [Scripts Documentation](../jeeves/scripts/shakira/README.md)
- [API Documentation](../jeeves/view/README.md)
- [Local Development Setup](../README.md#running-shake-to-report-flow-locally)
