import * as React from "react";

import styles from "styles/JiraIssues.scss";

interface Props {
  issues: {
    key: string;
    summary: string;
  }[];
}

const JiraIssues: React.FC<Props> = ({ issues }) => (
  <div className={styles.wrap}>
    <ul className={styles.list}>
      {issues.map(({ key, summary }, i) => {
        return (
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
            </a>
          </li>
        );
      })}
    </ul>
  </div>
);

export default JiraIssues;
