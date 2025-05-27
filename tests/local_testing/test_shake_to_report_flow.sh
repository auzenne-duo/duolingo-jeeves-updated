#!/bin/bash

# Usage: ./test_shake_to_report_flow.sh
# Make sure to update the paths to your log files below.

API_URL="http://localhost:8080/api/2/shakira/report_issue"

# Create a temp directory for this script run
TMPDIR=$(mktemp -d)
RESPONSE_JSON="$TMPDIR/response.json"

curl -X POST "$API_URL" \
  -F 'issueData={
    "project": "TES",
    "feature": "Path",
    "summary": "lily not responding / device not capturing inputs",
    "description": "this happens to me consistently on this device. i have reported many times before but not actually gotten resolution : / once i had to steal a device lab phone or a week to be able to test video call",
    "generatedDescription": "---\n\nGenerated info",
    "reporterEmail": "test@example.com"
  }' \
  -s > "$RESPONSE_JSON"

# Extract jiraIssueKey from the response
JIRA_ISSUE_KEY=$(jq -r '.issueKey' "$RESPONSE_JSON")

echo "Full JSON response:"
cat "$RESPONSE_JSON"

echo "issueKey from report_issue: $JIRA_ISSUE_KEY"

# Second call: upload artifacts
UPLOAD_API_URL="http://localhost:8080/api/2/shakira/upload_artifacts"
curl -X POST "$UPLOAD_API_URL" \
  -F "jiraIssueKey=$JIRA_ISSUE_KEY" \
  -F 'logfile1=@log1.txt' \
  -F 'logfile2=@log2.txt' \
  -F 'screenshot=@screenshot.jpeg'

# Optionally, clean up
rm -rf "$TMPDIR"
