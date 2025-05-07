import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { getQualityReportForArea } from "api/jeeves";
import styles from "components/quality-report/QualityReportForArea.module.scss";
import useDocumentTitle from "components/useDocumentTitle";

// Helper function to format dates
const formatDate = (dateString: string): string => {
  if (!dateString) {
    return "";
  }

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch (e) {
    return dateString;
  }
};

interface OpenIssue {
  key: string;
  title: string;
  assignee: string;
  creation_date: string;
  priority: string;
}

interface RouteParams {
  area: string;
  team?: string;
}

type SortField = "priority" | "key" | "assignee" | "creation_date" | "title";
type SortDirection = "asc" | "desc";

// Define a CSS class-based approach instead of inline styles
const openIssuesStyles = {
  assigneeColumn: {
    width: "150px",
  },
  backLink: {
    display: "inline-block",
    marginBottom: "20px",
  },
  dateColumn: {
    width: "150px",
  },
  ellipsis: {
    display: "block",
    maxWidth: "100%",
    overflow: "hidden" as const,
    textOverflow: "ellipsis" as const,
    whiteSpace: "nowrap" as const,
  },
  indexColumn: {
    textAlign: "center" as const,
    width: "50px",
  },
  keyColumn: {
    width: "120px",
  },
  priorityColumn: {
    width: "100px",
  },
  sortButton: {
    alignItems: "center",
    background: "none",
    border: "none",
    cursor: "pointer",
    display: "inline-flex",
    fontWeight: "bold",
    padding: 0,
  },
  sortIcon: {
    fontSize: "12px",
    marginLeft: "5px",
  },
  table: {
    border: "1px solid #ccc",
    borderCollapse: "collapse" as const,
    width: "100%",
  },
  tableContainer: {
    marginTop: "20px",
    width: "100%",
  },
  td: {
    borderBottom: "1px solid #ccc",
    borderRight: "1px solid #ccc",
    padding: "8px 12px",
  },
  th: {
    backgroundColor: "#f2f2f2",
    borderBottom: "1px solid #ccc",
    fontWeight: "bold",
    padding: "8px 12px",
    textAlign: "left" as const,
  },
  titleColumn: {
    maxWidth: "600px",
  },
};

const OpenIssuesPage = () => {
  const { area } = useParams<RouteParams>();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const team = queryParams.get("team") ?? undefined;
  const pillar = queryParams.get("pillar") ?? undefined;

  const [sortField, setSortField] = React.useState<SortField>("priority");
  const [sortDirection, setSortDirection] =
    React.useState<SortDirection>("desc");

  useDocumentTitle(`${team ?? area} Open Issues`);

  const { data, isLoading } = useQuery(["quality-report", area], () =>
    getQualityReportForArea(area ?? ""),
  );

  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Get the appropriate report data
  const report = team
    ? data?.teams?.find((t: JSONAPI.DetailedQualityReport) => t.title === team)
    : data;

  if (!report?.open_issues?.length) {
    return <div>No open issues found</div>;
  }

  // Build the back link
  const lang = location.pathname.split("/")[1];
  let backLink = `/${lang}/quality-report?pillar=${encodeURIComponent(pillar ?? "")}`;
  if (area) {
    backLink += `&area=${encodeURIComponent(area)}`;
  }
  if (team) {
    backLink += `&team=${encodeURIComponent(team)}`;
  }

  // Sort the open issues
  const sortedIssues = [...report.open_issues].sort((a, b) => {
    const aValue = (a as Record<string, string>)[sortField] || "";
    const bValue = (b as Record<string, string>)[sortField] || "";

    // Special handling for priority
    if (sortField === "priority") {
      const priorityOrder: Record<string, number> = {
        High: 4,
        Highest: 5,
        Low: 2,
        Lowest: 1,
        Medium: 3,
        Unprioritized: 0,
      };
      const aPriority =
        typeof aValue === "string" && aValue in priorityOrder
          ? priorityOrder[aValue]
          : 0;
      const bPriority =
        typeof bValue === "string" && bValue in priorityOrder
          ? priorityOrder[bValue]
          : 0;
      return sortDirection === "desc"
        ? bPriority - aPriority
        : aPriority - bPriority;
    }

    // Handle dates
    if (sortField === "creation_date") {
      const aDate = aValue ? new Date(aValue).getTime() : 0;
      const bDate = bValue ? new Date(bValue).getTime() : 0;

      return sortDirection === "desc" ? bDate - aDate : aDate - bDate;
    }

    // Default string comparison
    return sortDirection === "desc"
      ? bValue.localeCompare(aValue)
      : aValue.localeCompare(bValue);
  });

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      // Toggle sort direction if clicking the same field
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Default to descending order for a new field
      setSortField(field);
      setSortDirection("desc");
    }
  };

  // Render a sort indicator next to the active sort column
  const renderSortIndicator = (field: SortField) => {
    if (sortField !== field) {
      return null;
    }

    return (
      <span style={openIssuesStyles.sortIcon}>
        {sortDirection === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  return (
    <div className={styles.section}>
      <h1 className={styles.title}>{team ?? area} Open Issues</h1>
      <Link style={openIssuesStyles.backLink} to={backLink}>
        Back to Quality Report
      </Link>

      <div style={openIssuesStyles.tableContainer}>
        <table style={openIssuesStyles.table}>
          <thead>
            <tr>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.indexColumn,
                }}
              >
                #
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.keyColumn,
                }}
              >
                <button
                  onClick={() => handleSort("key")}
                  style={openIssuesStyles.sortButton}
                >
                  Key {renderSortIndicator("key")}
                </button>
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.priorityColumn,
                }}
              >
                <button
                  onClick={() => handleSort("priority")}
                  style={openIssuesStyles.sortButton}
                >
                  Priority {renderSortIndicator("priority")}
                </button>
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.assigneeColumn,
                }}
              >
                <button
                  onClick={() => handleSort("assignee")}
                  style={openIssuesStyles.sortButton}
                >
                  Assignee {renderSortIndicator("assignee")}
                </button>
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.dateColumn,
                }}
              >
                <button
                  onClick={() => handleSort("creation_date")}
                  style={openIssuesStyles.sortButton}
                >
                  Created {renderSortIndicator("creation_date")}
                </button>
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.titleColumn,
                }}
              >
                <button
                  onClick={() => handleSort("title")}
                  style={openIssuesStyles.sortButton}
                >
                  Title {renderSortIndicator("title")}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedIssues.map((issue, index: number) => {
              // Handle the possibility of missing fields
              const fullIssue: OpenIssue = {
                assignee: (issue as Record<string, string>).assignee || "",
                creation_date:
                  (issue as Record<string, string>).creation_date || "",
                key: issue.key,
                priority: (issue as Record<string, string>).priority || "",
                title: issue.title,
              };

              return (
                <tr key={fullIssue.key}>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.indexColumn,
                    }}
                  >
                    {index + 1}
                  </td>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.keyColumn,
                    }}
                  >
                    <a
                      href={`https://duolingo.atlassian.net/browse/${fullIssue.key}`}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      {fullIssue.key}
                    </a>
                  </td>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.priorityColumn,
                    }}
                  >
                    <div
                      style={openIssuesStyles.ellipsis}
                      title={fullIssue.priority}
                    >
                      {fullIssue.priority || "None"}
                    </div>
                  </td>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.assigneeColumn,
                    }}
                  >
                    <div
                      style={openIssuesStyles.ellipsis}
                      title={fullIssue.assignee}
                    >
                      {fullIssue.assignee || "Unassigned"}
                    </div>
                  </td>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.dateColumn,
                    }}
                  >
                    {formatDate(fullIssue.creation_date)}
                  </td>
                  <td
                    style={{
                      ...openIssuesStyles.td,
                      ...openIssuesStyles.titleColumn,
                    }}
                  >
                    <div
                      style={openIssuesStyles.ellipsis}
                      title={fullIssue.title}
                    >
                      {fullIssue.title}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OpenIssuesPage;
