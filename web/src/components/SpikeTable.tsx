import { formatISO } from "date-fns";
import * as React from "react";
import { Link } from "react-router-dom";

import Table from "components/Table";
import styles from "styles/SpikeTable.scss";

interface Props {
  date: Date | undefined;
  isLoading?: boolean;
  language: JSONAPI.LanguageId;
  linkFilter?: JSONAPI.ShakeToReportCategory;
  spikes: [number, string][];
}

const SpikeTable = ({
  date,
  isLoading,
  language,
  linkFilter,
  spikes,
}: Props) => (
  <Table className={styles.table}>
    <thead>
      <tr>
        <th colSpan={2}>
          Trending words on{" "}
          {date ? formatISO(date, { representation: "date" }) : null}
        </th>
      </tr>
      <tr>
        <th>Spikiness</th>
        <th>Word</th>
      </tr>
    </thead>
    <tbody>
      {spikes.map(([value, word]) => {
        const params = new URLSearchParams();
        if (linkFilter) {
          params.set("filter", linkFilter);
        }
        params.set("q", word);
        return (
          <tr key={word}>
            <td>{value.toFixed(1)}</td>
            <td>
              <Link to={`/${language}/analysis?${params.toString()}`}>
                {word}
              </Link>
            </td>
          </tr>
        );
      })}
      {!spikes.length && !isLoading ? (
        <tr>
          <td colSpan={2}>No data is available for this date.</td>
        </tr>
      ) : null}
    </tbody>
  </Table>
);

export default SpikeTable;
