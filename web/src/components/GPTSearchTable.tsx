import * as React from "react";

import GPTSearchCell from "components/GPTSearchCell";
import Table from "components/Table";
import styles from "styles/GPTSearchTable.scss";

interface Props {
  docs: JSONAPI.GPTSearchResult[];
}

const GPTSearchTable = ({ docs }: Props) => {
  const hasTranslation = docs.find(d => d.translated_text);
  return (
    <Table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.document}>Document</th>
          <th>Text (hover to see full text)</th>
          {hasTranslation && <th>Translation</th>}
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
            <GPTSearchCell cell={d.original_text} />
            {hasTranslation && <GPTSearchCell cell={d.translated_text} />}
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

export default GPTSearchTable;
