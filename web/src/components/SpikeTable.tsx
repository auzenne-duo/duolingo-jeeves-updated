import * as React from "react";
import { Link } from "react-router-dom";

import { LanguageId } from "components/LanguagePicker";
import Loading from "components/Loading";
import Table from "components/Table";
import styles from "styles/SpikeTable.scss";

interface Props {
  date: string;
  isLoading?: boolean;
  language: LanguageId;
  spikes: [number, string][];
}

const SpikeTable: React.FC<Props> = ({ date, isLoading, language, spikes }) => (
  <Table className={styles.table}>
    <thead>
      <tr>
        <th colSpan={2}>Trending words on {date}</th>
      </tr>
      <tr>
        <th>Spikiness</th>
        <th>Word</th>
      </tr>
    </thead>
    <tbody>
      {spikes.map(([value, word]) => (
        <tr key={word}>
          <td>{value.toFixed(1)}</td>
          <td>
            <Link to={`/${language}/analysis?q=${encodeURIComponent(word)}`}>
              {word}
            </Link>
          </td>
        </tr>
      ))}
      {!spikes.length ? (
        <tr>
          <td colSpan={2}>
            {isLoading ? (
              <Loading type="table-cell" />
            ) : (
              "No data is available for this date."
            )}
          </td>
        </tr>
      ) : null}
    </tbody>
  </Table>
);

export default SpikeTable;
