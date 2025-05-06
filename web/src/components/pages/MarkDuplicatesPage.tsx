import * as React from "react";
import { useLocation } from "react-router-dom";

import styles from "../NamedSection.module.scss";
import { fullyConnectDuplicates } from "api/jeeves";

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

  // Parse jira_issues from URL query parameters
  const searchParams = new URLSearchParams(location.search);
  const jiraIssuesParam = searchParams.get("jira_issues") ?? "";
  const jiraIssues = jiraIssuesParam.split(",").filter(Boolean);

  // State to track which tickets are selected
  const [selectedTickets, setSelectedTickets] =
    React.useState<string[]>(jiraIssues);

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
        message: `Successfully connected ${selectedTickets.length} tickets as duplicates. Status: ${response.overall}`,
        success: response.overall.startsWith("SUCCESS"),
      });
    } catch (error) {
      setResult({
        message: `Error connecting duplicates: ${error instanceof Error ? error.message : String(error)}`,
        success: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.section}>
      <h2>Connect Multiple JIRA Issues as Duplicates</h2>
      <div className={styles.content}>
        {jiraIssues.length === 0 ? (
          <p>
            No JIRA issues provided. Use the URL parameter{" "}
            <code>jira_issues</code> with a comma-separated list of issues.
          </p>
        ) : (
          <>
            <p>
              Select the JIRA issues you want to mark as duplicates. All
              selected issues will be linked together.
            </p>

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
              {jiraIssues.map(ticketKey => (
                <div
                  key={ticketKey}
                  style={{
                    alignItems: "center",
                    backgroundColor: selectedTickets.includes(ticketKey)
                      ? "#F4F9FF"
                      : "transparent",
                    borderRadius: "3px",
                    display: "flex",
                    marginBottom: "8px",
                    padding: "5px",
                  }}
                >
                  <input
                    checked={selectedTickets.includes(ticketKey)}
                    id={`ticket-${ticketKey}`}
                    onChange={() => handleTicketToggle(ticketKey)}
                    style={{ marginRight: "10px" }}
                    type="checkbox"
                  />
                  <label
                    htmlFor={`ticket-${ticketKey}`}
                    style={{
                      alignItems: "center",
                      cursor: "pointer",
                      display: "flex",
                    }}
                  >
                    <JiraLink ticketKey={ticketKey} />
                  </label>
                </div>
              ))}
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
              {isLoading ? "Processing..." : "Connect Selected as Duplicates"}
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
        )}
      </div>
    </div>
  );
};

export default MarkDuplicatesPage;
