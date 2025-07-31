# Shakira Scripts

This directory contains utility scripts for managing Duolingo's "Shake-to-report" bug reporting system (Shakira).

## Automation & Scheduling Summary

| Script                      | Automation    | Schedule             | Environment     | Trigger             |
| --------------------------- | ------------- | -------------------- | --------------- | ------------------- |
| `create_jira_features.py`   | Jenkins CI/CD | On production deploy | Production only | Deployment pipeline |
| `get_duplicate_graph.py`    | Manual only   | N/A                  | Local           | Manual execution    |
| `send_bug_digest_emails.py` | AWS ECS       | Mondays 4:00 PM UTC  | Production only | Cron schedule       |

## Common Dependencies

All scripts use:

- `jeeves` registry system for dependency injection
- Duolingo's internal logging and notification systems
- JIRA API integration through ShakiraJiraApiClient

### Environment Setup

1. Set up Python environment per project README
2. Configure required environment variables (see individual script requirements)
3. Ensure JIRA API access is properly configured

## create_jira_features.py

**Purpose**: Ensures all features defined in the jira_features.py config exist in the necessary JIRA projects.

**Input**: Feature definitions from `jeeves/config/jira_features.py`

**Output**: Creates missing features as custom field options in JIRA projects (DLAA, DLAI, DLAW)

**Requirements**:

- Environment variables:
  - `SHAKIRA_JIRA_USERNAME_WEB`: JIRA username
  - `SHAKIRA_JIRA_API_TOKEN_WEB`: JIRA API token

**Usage**:

```bash
python jeeves/scripts/shakira/create_jira_features.py
```

**Example Input** (from jira_features.py):

```python
JIRA_FEATURES = {
    "Monetization": {
        "no_area_monetization": {
            "Acquisition": {
                "Immersive subscriptions": ["immersive"],
                "Hearts / Unlimited Hearts": ["heart"],
                "Subscription hooks": [],
                "Super Upsell": [],
                "Family Plan": [],
                "Legendary": ["Legendarize"],
            },
            "Subscription Packaging": {
                "Purchase Flow": ["purchase page", "purchase screen", "purchase step"],
                "Duo on Path": [],
                "Super": [],
                "New Years Promo": [],
                "Student Plan": [],
                "Streak Society Promo": [],
                "Energy Retier": [],
            },
        },
    },
}
```

**Example Output**:

```
Identified features to create
['Immersive subscriptions', 'Hearts / Unlimited Hearts', 'Subscription hooks', 'Super Upsell', 'Family Plan', 'Legendary', 'Purchase Flow', 'Duo on Path', 'Super', 'New Years Promo', 'Student Plan', 'Streak Society Promo', 'Energy Retier']
```

**What it does**:

- Reads all feature names from the config
- Checks which features don't exist in JIRA
- Creates missing features as custom field options
- Exits silently if all features already exist

**Automation**:

- **When**: Runs automatically during production deployments via Jenkins
- **Where**: `jenkins-build.sh` - executed after Docker image deployment
- **Environment**: Production only - uses `jira-automation@duolingo.com` credentials
- **Trigger**: Every production deployment

## get_duplicate_graph.py

**Purpose**: Analyzes and retrieves duplicate ticket relationships in JIRA for debugging and investigation.

**Input**: JIRA ticket keys as command line arguments

**Output**: Graph of related/duplicate tickets with keys, summaries, and resolutions

**Requirements**:

- Environment variables:
  - `JIRA_USERNAME`: @duolingo email address
  - `JIRA_API_TOKEN`: JIRA API token (generate from https://id.atlassian.com/manage-profile/security/api-tokens)

**Usage**:

```bash
python jeeves/scripts/shakira/get_duplicate_graph.py DLAA-10000 DLAA-10001
```

**Example Input**:

```bash
python jeeves/scripts/shakira/get_duplicate_graph.py DLAA-12345 DLAA-12346
```

**Example Output**:

```
DLAA-12345
DLAA-12346
DLAA-12347
DLAA-12348
DLAA-12349
```

**What it does**:

- Takes JIRA ticket keys as arguments
- Builds a graph of related/duplicate tickets
- Outputs all reachable issue keys from the provided tickets
- Can be modified to also print summaries and resolutions (commented in script)

**Automation**:

- **When**: Manual execution only - no automated scheduling
- **Where**: Run locally or in development environments
- **Use Case**: Debugging duplicate ticket relationships

## send_bug_digest_emails.py

**Purpose**: Sends weekly digest emails to bug reporters with statistics about their reported bugs.

**Input**: Bug reporting data from JIRA and internal systems

**Output**: Personalized HTML emails sent to bug reporters

**Features**:

- Unsubscribe list management
- Only sends emails to reporters with recent activity
- Uses HTML templates for email formatting
- Includes links to Jeeves for detailed views

**Email Statistics Included**:

- Total bugs reported
- Total resolved bug reports
- Bugs reported in the last week
- Bug reports resolved in the last week

**Unsubscription**:
Add your @duolingo.com email address to the `_UNSUBSCRIBED` list in the script.

**Usage**:

```bash
python jeeves/scripts/shakira/send_bug_digest_emails.py
```

**Example Input** (data collected from JIRA):

```python
# Internal data structure
reporter_stats = {
    "user@duolingo.com": {
        "total_bugs": 15,
        "total_resolved": 12,
        "bugs_last_week": 2,
        "resolved_last_week": 1,
        "recent_resolved_bugs": ["DLAA-12345", "DLAA-12346"]
    }
}
```

**Example Output** (HTML email sent):

```html
Subject: Your Bug Report Digest - Week of Dec 1, 2024 Hi user@duolingo.com,
Here's your bug reporting activity for the past week: 📊 Your Stats: • Total
bugs reported: 15 • Total resolved: 12 • Bugs reported this week: 2 • Bugs
resolved this week: 1 ✅ Recently Resolved: • DLAA-12345 - Hearts not refilling
properly • DLAA-12346 - App crashes on startup View your full history: [Link to
Jeeves]
```

**What it does**:

- Collects bug reporting statistics per reporter
- Generates personalized HTML emails
- Sends emails via Duolingo's notification system
- Respects unsubscribe preferences

**Automation**:

- **When**: Every Monday at 4:00 PM UTC/12:00 PM Eastern (`cron(0 16 ? * MON *)`)
- **Where**: [AWS ECS task](https://us-east-1.console.aws.amazon.com/ecs/v2/task-definitions/duolingo-jeeves-email-sender-prod?status=ACTIVE&region=us-east-1) (`duolingo-jeeves-email-sender`)
- **Environment**: Production only
- **Configuration**: `galaxy/prod/email-sender.json` and `galaxy/dev/email-sender.json`
