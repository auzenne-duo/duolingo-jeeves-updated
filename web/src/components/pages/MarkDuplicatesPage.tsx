import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";

import track from "../../track";
import styles from "../NamedSection.module.scss";
import { fullyConnectDuplicates, getJiraIssueDetails } from "api/jeeves";
import type { JiraIssueDetails } from "api/jeeves";

/**
 * Creates a JIRA URL from a ticket key
 */
const getJiraUrl = (ticketKey: string): string =>
  `https://duolingo.atlassian.net/browse/${ticketKey}`;

/**
 * Creates a linked JIRA ticket reference
 */
const JiraLink: React.FC<{ ticketKey: string }> = ({ ticketKey }) => (
  <a
    href={getJiraUrl(ticketKey)}
    rel="noopener noreferrer"
    style={{ color: "#0052CC", fontWeight: "bold" }}
    target="_blank"
  >
    {ticketKey}
  </a>
);

const MarkDuplicatesPage: React.FC = () => {
  const location = useLocation();
  const history = useHistory();
  const [isLoading, setIsLoading] = React.useState(false);
  const [result, setResult] = React.useState<{
    message: string;
    success: boolean;
  } | null>(null);
  const [issueDetails, setIssueDetails] = React.useState<
    JiraIssueDetails[] | null
  >(null);
  const [detailsLoading, setDetailsLoading] = React.useState(false);

  // Parse jira_issues from URL query parameters
  const searchParams = new URLSearchParams(location.search);
  const urlJiraIssuesParam = searchParams.get("jira_issues") ?? "";
  const urlJiraIssues = React.useMemo(
    () => urlJiraIssuesParam.split(",").filter(Boolean),
    [urlJiraIssuesParam],
  );

  // State for input field
  const [inputValue, setInputValue] = React.useState(urlJiraIssuesParam);
  const [jiraIssues, setJiraIssues] = React.useState<string[]>(urlJiraIssues);

  // State to track which tickets are selected
  const [selectedTickets, setSelectedTickets] =
    React.useState<string[]>(urlJiraIssues);

  // Update jiraIssues when URL changes

  React.useEffect(() => {
    setJiraIssues(urlJiraIssues);
    setSelectedTickets(urlJiraIssues);
    setInputValue(urlJiraIssuesParam);
  }, [urlJiraIssues, urlJiraIssuesParam]);

  // Load JIRA issue details when jiraIssues changes
  React.useEffect(() => {
    // Track page view event
    track("mark_duplicates_page_view", {
      jira_issues: jiraIssues.join(","),
      num_jira_issues: jiraIssues.length,
    });

    if (jiraIssues.length === 0) {
      setIssueDetails(null);
      return;
    }
    setDetailsLoading(true);
    getJiraIssueDetails(jiraIssues)
      .then(setIssueDetails)
      .catch(() => setIssueDetails(null))
      .finally(() => setDetailsLoading(false));
  }, [jiraIssues]);

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const handleLoadIssues = () => {
    const issues = inputValue
      .split(",")
      .map(issue => issue.trim().toUpperCase())
      .filter(Boolean);

    if (issues.length === 0) {
      setResult({
        message: "Please enter at least one valid JIRA issue key.",
        success: false,
      });
      return;
    }

    // Validate JIRA ticket format (capital letters + dash + number)
    const jiraPattern = /^[A-Z]+-\d+$/;
    const invalidIssues = issues.filter(issue => !jiraPattern.test(issue));

    if (invalidIssues.length > 0) {
      setResult({
        message: `Invalid JIRA ticket format: ${invalidIssues.join(", ")}. Expected format: LETTERS-NUMBER (e.g., DLAI-52067)`,
        success: false,
      });
      return;
    }

    setJiraIssues(issues);
    setSelectedTickets(issues);
    setResult(null); // Clear any previous results

    // Update URL parameters to sync with input
    const newSearchParams = new URLSearchParams(location.search);
    if (issues.length > 0) {
      newSearchParams.set("jira_issues", issues.join(","));
    } else {
      newSearchParams.delete("jira_issues");
    }

    // Navigate to the new URL with updated parameters
    history.replace(`${location.pathname}?${newSearchParams.toString()}`);
  };

  const handleTicketToggle = (ticketKey: string) => {
    setSelectedTickets(prev =>
      prev.includes(ticketKey)
        ? prev.filter(key => key !== ticketKey)
        : [...prev, ticketKey],
    );
  };

  const handleSelectAll = () => {
    setSelectedTickets(jiraIssues);
  };

  const handleSelectNone = () => {
    setSelectedTickets([]);
  };

  const handleConnectDuplicates = async () => {
    if (selectedTickets.length < 2) {
      setResult({
        message:
          "At least two JIRA issues must be selected to mark as duplicates",
        success: false,
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fullyConnectDuplicates(selectedTickets);
      setResult({
        message: `Successfully marked ${selectedTickets.length} tickets as duplicates. ${response.overall}`,
        success: response.overall.startsWith("SUCCESS"),
      });
      // Track connect event (success)
      track("mark_duplicates_connect", {
        jira_issues: selectedTickets.join(","),
        status: response.overall,
        success: response.overall.startsWith("SUCCESS"),
      });
    } catch (error) {
      setResult({
        message: `Error marking duplicates: ${error instanceof Error ? error.message : String(error)}`,
        success: false,
      });
      // Track connect event (failure)
      track("mark_duplicates_connect", {
        jira_issues: selectedTickets.join(","),
        status: error instanceof Error ? error.message : String(error),
        success: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.section}>
      <h2>Mark Multiple JIRA Issues as Duplicates</h2>
      <div className={styles.content}>
        <div style={{ marginBottom: "20px" }}>
          <label
            htmlFor="jira-input"
            style={{
              display: "block",
              fontWeight: "bold",
              marginBottom: "8px",
            }}
          >
            Enter JIRA Issue Keys (comma-separated):
          </label>
          <div style={{ alignItems: "center", display: "flex", gap: "10px" }}>
            <input
              id="jira-input"
              onChange={handleInputChange}
              placeholder="e.g., DLAI-52067,DLAI-52066,DLAI-54218"
              style={{
                border: "1px solid #DFE1E6",
                borderRadius: "4px",
                flex: 1,
                fontSize: "14px",
                padding: "8px 12px",
              }}
              type="text"
              value={inputValue}
            />
            <button
              onClick={handleLoadIssues}
              style={{
                backgroundColor: "#0052CC",
                border: "none",
                borderRadius: "4px",
                color: "white",
                cursor: "pointer",
                fontSize: "14px",
                padding: "8px 16px",
              }}
            >
              Load Issues
            </button>
          </div>
        </div>

        {result && (
          <div
            style={{
              backgroundColor: result.success ? "#E3FCEF" : "#FFEBE6",
              borderRadius: "3px",
              color: result.success ? "#006644" : "#DE350B",
              marginBottom: "20px",
              padding: "10px",
            }}
          >
            {result.message}
          </div>
        )}

        {jiraIssues.length === 0 ? (
          <p>
            Enter JIRA issue keys above or use the URL parameter{" "}
            <code>jira_issues</code> with a comma-separated list of issues.
          </p>
        ) : detailsLoading ? (
          <p>Loading JIRA issue details...</p>
        ) : issueDetails ? (
          <>
            <p>
              Select the JIRA issues you want to mark as duplicates. A parent
              ticket will be created and remain open, while all other tickets
              will be closed as duplicates of it.
            </p>

            {jiraIssues.length !== issueDetails.length && (
              <div
                style={{
                  backgroundColor: "#FFEBE6",
                  borderRadius: "3px",
                  color: "#DE350B",
                  marginBottom: "15px",
                  padding: "10px",
                }}
              >
                Warning: Some JIRA issues could not be found and are not shown
                below. Please check your input.
              </div>
            )}

            <div style={{ marginBottom: "15px" }}>
              <button
                onClick={handleSelectAll}
                style={{
                  backgroundColor: "#F4F5F7",
                  border: "1px solid #DFE1E6",
                  borderRadius: "3px",
                  color: "#172B4D",
                  cursor: "pointer",
                  fontSize: "14px",
                  marginRight: "10px",
                  padding: "5px 10px",
                }}
              >
                Select All
              </button>
              <button
                onClick={handleSelectNone}
                style={{
                  backgroundColor: "#F4F5F7",
                  border: "1px solid #DFE1E6",
                  borderRadius: "3px",
                  color: "#172B4D",
                  cursor: "pointer",
                  fontSize: "14px",
                  padding: "5px 10px",
                }}
              >
                Clear All
              </button>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <table
                style={{
                  background: "#fff",
                  borderCollapse: "separate",
                  borderSpacing: "0 8px",
                  width: "100%",
                }}
              >
                <thead>
                  <tr style={{ background: "#F4F5F7" }}>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    />
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      JIRA Key
                    </th>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      Title
                    </th>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      Status
                    </th>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      Date Reported
                    </th>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      Assignee
                    </th>
                    <th
                      style={{
                        borderBottom: "2px solid #DFE1E6",
                        fontSize: 18,
                        fontWeight: 700,
                        padding: "12px 16px",
                        textAlign: "left",
                      }}
                    >
                      Feature
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {issueDetails.map((issue, idx) => (
                    <tr
                      key={issue.key}
                      style={{
                        backgroundColor: selectedTickets.includes(issue.key)
                          ? "#F4F9FF"
                          : idx % 2 === 0
                            ? "#FAFBFC"
                            : "#fff",
                        borderRadius: 8,
                      }}
                    >
                      <td style={{ padding: "10px 16px" }}>
                        <input
                          checked={selectedTickets.includes(issue.key)}
                          id={`ticket-${issue.key}`}
                          onChange={() => handleTicketToggle(issue.key)}
                          type="checkbox"
                        />
                      </td>
                      <td style={{ fontWeight: 600, padding: "10px 16px" }}>
                        <JiraLink ticketKey={issue.key} />
                      </td>
                      <td style={{ padding: "10px 16px" }}>{issue.title}</td>
                      <td style={{ padding: "10px 16px" }}>{issue.status}</td>
                      <td style={{ padding: "10px 16px" }}>
                        {issue.date_reported
                          ? new Date(issue.date_reported).toLocaleString()
                          : ""}
                      </td>
                      <td style={{ padding: "10px 16px" }}>{issue.assignee}</td>
                      <td style={{ padding: "10px 16px" }}>{issue.feature}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              disabled={isLoading || selectedTickets.length < 2}
              onClick={handleConnectDuplicates}
              style={{
                backgroundColor: "#0052CC",
                border: "none",
                borderRadius: "3px",
                color: "white",
                cursor:
                  isLoading || selectedTickets.length < 2
                    ? "not-allowed"
                    : "pointer",
                fontSize: "16px",
                opacity: selectedTickets.length < 2 ? 0.6 : 1,
                padding: "10px 20px",
              }}
            >
              {isLoading ? "Processing..." : "Close Selected as Duplicates"}
            </button>
          </>
        ) : (
          <p>Could not load JIRA issue details.</p>
        )}
      </div>
    </div>
  );
};

export default MarkDuplicatesPage;
