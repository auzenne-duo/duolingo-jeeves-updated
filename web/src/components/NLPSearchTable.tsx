import * as React from "react";

import styles from "styles/NLPSearchTable.scss";

import NLPSearchCell from "./NLPSearchCell";
import Table from "./Table";

interface Props {
  docs: JSONAPI.NLPSearchResult[];
}

const NLPSearchTable = ({ docs }: Props) => {
  const hasTranslation = docs.find(d => d.translated_text);
  return (
    <Table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.document}>Document</th>
          <th>Text (Hover to see full text)</th>
          {hasTranslation && <th>Translation</th>}
          <th className={styles.score}>Score</th>
        </tr>
      </thead>
      <tbody>
        {docs.map(d => (
          <tr key={d.uid}>
            <td className={styles.document}>
              <b>Source:</b> {d.origin}
              <br />
              <b>Date:</b> {new Date(d.datetime).toLocaleString()}
            </td>
            <NLPSearchCell cell={d.original_text} />
            {hasTranslation && <NLPSearchCell cell={d.translated_text} />}
            <td className={styles.score}>{d.score.toFixed(4)}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

export default NLPSearchTable;
