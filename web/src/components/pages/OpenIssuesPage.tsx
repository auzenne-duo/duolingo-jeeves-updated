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

interface OpenIssue {
  key: string;
  title: string;
  assignee: string;
  creation_date: string;
}

interface RouteParams {
  area: string;
  team?: string;
}

const OpenIssuesPage = () => {
  const { area } = useParams<RouteParams>();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const team = queryParams.get("team") ?? undefined;
  const pillar = queryParams.get("pillar") ?? undefined;

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
                Key
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.assigneeColumn,
                }}
              >
                Assignee
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.dateColumn,
                }}
              >
                Creation Date
              </th>
              <th
                style={{
                  ...openIssuesStyles.th,
                  ...openIssuesStyles.titleColumn,
                }}
              >
                Title
              </th>
            </tr>
          </thead>
          <tbody>
            {report.open_issues?.map((issue, index: number) => {
              // Handle the possibility of missing assignee and creation_date
              const fullIssue: OpenIssue = {
                assignee: issue.assignee || "",
                creation_date: issue.creation_date || "",
                key: issue.key,
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
