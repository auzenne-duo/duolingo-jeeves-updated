import cn from "classnames";
import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";

import track from "../../track";
import styles from "../NamedSection.module.scss";
import type { JiraIssueDetails } from "api/jeeves";
import { fullyConnectDuplicates, getJiraIssueDetails } from "api/jeeves";

import pageStyles from "./MarkDuplicatesPage.module.scss";

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
    className={pageStyles.jiraLink}
    href={getJiraUrl(ticketKey)}
    rel="noopener noreferrer"
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
  const createParentTicket =
    searchParams.get("create_parent_ticket") !== "false";
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
      create_parent_ticket: createParentTicket,
      jira_issues: jiraIssues,
      num_jira_issues: jiraIssues.length,
    });

    // For no-parent flow we don't need additional details
    if (!createParentTicket) {
      setIssueDetails(null);
      return;
    }

    if (jiraIssues.length === 0) {
      setIssueDetails(null);
      return;
    }

    setDetailsLoading(true);
    getJiraIssueDetails(jiraIssues)
      .then(setIssueDetails)
      .catch(() => setIssueDetails(null))
      .finally(() => setDetailsLoading(false));
  }, [jiraIssues, createParentTicket]);

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
    const ticketsToProcess = createParentTicket ? selectedTickets : jiraIssues;

    if (ticketsToProcess.length < 2) {
      setResult({
        message: "At least two JIRA issues are required to mark as duplicates.",
        success: false,
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fullyConnectDuplicates(
        ticketsToProcess,
        createParentTicket,
      );

      const successMessage = createParentTicket
        ? `Successfully marked ${ticketsToProcess.length} tickets as duplicates.`
        : `Successfully closed ${ticketsToProcess[0]} as a duplicate of ${ticketsToProcess.length - 1} other ticket${ticketsToProcess.length - 1 === 1 ? "" : "s"}.`;

      const successFlag = response.overall.startsWith("SUCCESS");
      setResult({
        message: `${successMessage} ${response.overall}`,
        success: successFlag,
      });

      track("mark_duplicates_connect", {
        create_parent_ticket: createParentTicket,
        jira_issues: ticketsToProcess,
        status: response.overall,
        success: successFlag,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      setResult({
        message: `Error marking duplicates: ${errorMessage}`,
        success: false,
      });
      // Track connect event (failure)
      track("mark_duplicates_connect", {
        create_parent_ticket: createParentTicket,
        jira_issues: ticketsToProcess,
        status: errorMessage,
        success: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.section}>
      <div className={styles.content}>
        <div className={pageStyles.inputGroup}>
          <label htmlFor="jira-input">
            Enter JIRA Issue Keys (comma-separated):
          </label>
          <div className={pageStyles.inputRow}>
            <input
              className={pageStyles.textInput}
              id="jira-input"
              onChange={handleInputChange}
              placeholder="e.g., DLAI-52067,DLAI-52066,DLAI-54218"
              type="text"
              value={inputValue}
            />
            <button
              className={pageStyles.loadButton}
              onClick={handleLoadIssues}
            >
              Load Issues
            </button>
          </div>
        </div>

        {result && (
          <div
            className={
              result.success
                ? `${pageStyles.warningBox} ${pageStyles.success}`
                : `${pageStyles.warningBox} ${pageStyles.error}`
            }
          >
            {result.message}
          </div>
        )}

        {createParentTicket ? (
          jiraIssues.length === 0 ? (
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
                <div className={`${pageStyles.warningBox} ${pageStyles.error}`}>
                  Warning: Some JIRA issues could not be found and are not shown
                  below. Please check your input.
                </div>
              )}

              <div className={pageStyles.selectButtons}>
                <button
                  className={pageStyles.secondaryButton}
                  onClick={handleSelectAll}
                >
                  Select All
                </button>
                <button
                  className={pageStyles.secondaryButton}
                  onClick={handleSelectNone}
                >
                  Clear All
                </button>
              </div>

              <div className={pageStyles.ticketsTable}>
                <table>
                  <thead>
                    <tr>
                      <th />
                      <th>JIRA Key</th>
                      <th>Title</th>
                      <th>Status</th>
                      <th>Date Reported</th>
                      <th>Assignee</th>
                      <th>Feature</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issueDetails.map((issue, idx) => (
                      <tr
                        className={cn(
                          pageStyles.row,
                          selectedTickets.includes(issue.key)
                            ? pageStyles.rowSelected
                            : idx % 2 === 0
                              ? pageStyles.rowEven
                              : pageStyles.rowOdd,
                        )}
                        key={issue.key}
                      >
                        <td className={pageStyles.cell}>
                          <input
                            checked={selectedTickets.includes(issue.key)}
                            id={`ticket-${issue.key}`}
                            onChange={() => handleTicketToggle(issue.key)}
                            type="checkbox"
                          />
                        </td>
                        <td className={cn(pageStyles.cell, pageStyles.bold)}>
                          <JiraLink ticketKey={issue.key} />
                        </td>
                        <td className={pageStyles.cell}>{issue.title}</td>
                        <td className={pageStyles.cell}>{issue.status}</td>
                        <td className={pageStyles.cell}>
                          {issue.date_reported
                            ? new Date(issue.date_reported).toLocaleString()
                            : ""}
                        </td>
                        <td className={pageStyles.cell}>{issue.assignee}</td>
                        <td className={pageStyles.cell}>{issue.feature}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <button
                className={pageStyles.primaryActionButton}
                disabled={isLoading || selectedTickets.length < 2}
                onClick={handleConnectDuplicates}
              >
                {isLoading
                  ? "Processing..."
                  : createParentTicket
                    ? "CREATE PARENT TICKET AND CLOSE SELECTED AS DUPLICATE"
                    : "CLOSE AS DUPLICATE"}
              </button>
            </>
          ) : (
            <p>Could not load JIRA issue details.</p>
          )
        ) : jiraIssues.length > 1 ? (
          <>
            <p className={pageStyles.noParentMessage}>
              {"Mark "}
              <JiraLink ticketKey={jiraIssues[0]} />
              {" as a duplicate of "}
              {jiraIssues.slice(1).map((key, idx) => (
                <React.Fragment key={key}>
                  <JiraLink ticketKey={key} />
                  {idx < jiraIssues.slice(1).length - 1 ? ", " : ""}
                </React.Fragment>
              ))}
              {/* No titles in no-parent flow */}
            </p>
            <button
              className={pageStyles.primaryActionButton}
              disabled={isLoading}
              onClick={handleConnectDuplicates}
            >
              {isLoading ? "Processing..." : "CLOSE AS DUPLICATE"}
            </button>
          </>
        ) : (
          <p>Enter at least two JIRA issue keys above.</p>
        )}
      </div>
    </div>
  );
};

export default MarkDuplicatesPage;
