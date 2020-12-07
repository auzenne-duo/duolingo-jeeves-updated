import * as React from "react";

import { JiraIssueLink, Ticket } from "api";
import styles from "styles/JiraIssues.scss";

const isTicket = (issue: JiraIssueLink | Ticket): issue is Ticket =>
  "document_id" in issue;

interface Props {
  issues: (JiraIssueLink | Ticket)[];
}

const JiraIssues: React.FC<Props> = ({ issues }) => (
  <div className={styles.wrap}>
    <ul className={styles.list}>
      {issues.map((issue, i) => {
        const key = isTicket(issue)
          ? (issue.issue_key as string)
          : ((issue.inwardIssue?.key ?? issue.outwardIssue?.key) as string);
        const title = isTicket(issue)
          ? issue.header_text
          : ((issue.inwardIssue?.fields.summary ??
              issue.outwardIssue?.fields.summary) as string);
        return (
          <li className={styles.item} key={i}>
            <a
              className={styles.link}
              href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
                key,
              )}`}
              title={title}
            >
              <span className={styles.key}>{key}</span>
              <span className={styles.title}>{title}</span>
            </a>
          </li>
        );
      })}
    </ul>
  </div>
);

export default JiraIssues;
