import * as React from "react";
import { useLocation } from "react-router-dom";

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
  const jiraIssuesParam = searchParams.get("jira_issues") ?? "";
  const jiraIssues = React.useMemo(
    () => jiraIssuesParam.split(",").filter(Boolean),
    [jiraIssuesParam],
  );

  // State to track which tickets are selected
  const [selectedTickets, setSelectedTickets] =
    React.useState<string[]>(jiraIssues);

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
        message: `Successfully marked ${selectedTickets.length} tickets as duplicates. Status: ${response.overall}`,
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
        {jiraIssues.length === 0 ? (
          <p>
            No JIRA issues provided. Use the URL parameter{" "}
            <code>jira_issues</code> with a comma-separated list of issues.
          </p>
        ) : detailsLoading ? (
          <p>Loading JIRA issue details...</p>
        ) : issueDetails ? (
          <>
            <p>
              Select the JIRA issues you want to mark as duplicates. All
              selected issues will be linked together.
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
              {isLoading ? "Processing..." : "Mark Selected as Duplicates"}
            </button>

            {result && (
              <div
                style={{
                  backgroundColor: result.success ? "#E3FCEF" : "#FFEBE6",
                  borderRadius: "3px",
                  color: result.success ? "#006644" : "#DE350B",
                  marginTop: "20px",
                  padding: "10px",
                }}
              >
                {result.message}
              </div>
            )}
          </>
        ) : (
          <p>Could not load JIRA issue details.</p>
        )}
      </div>
    </div>
  );
};

export default MarkDuplicatesPage;
