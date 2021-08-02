import * as React from "react";

import JiraStatus from "components/JiraStatus";
import styles from "styles/JiraIssues.scss";

interface Props {
  issues: {
    key: string;
    status?: string;
    summary: string;
  }[];
}

const JiraIssues = ({ issues }: Props) => (
  <div className={styles.wrap}>
    <ul className={styles.list}>
      {issues.map(({ key, status, summary }, i) => (
        <li className={styles.item} key={i}>
          <a
            className={styles.link}
            href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
              key,
            )}`}
            title={summary}
          >
            <span className={styles.key}>{key}</span>
            <span className={styles.title}>{summary}</span>
            {status ? (
              <JiraStatus className={styles.status} status={status} />
            ) : null}
          </a>
        </li>
      ))}
    </ul>
  </div>
);

export default JiraIssues;
