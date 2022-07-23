import { encodeURLSearchParams } from "util";

import { formatISO } from "date-fns";
import * as React from "react";
import { Link } from "react-router-dom";

import ConfirmButton from "components/ConfirmButton";
import Table from "components/Table";
import styles from "styles/SpikeTable.scss";

interface Props {
  date: Date | undefined;
  isLoading?: boolean;
  language: JSONAPI.LanguageId;
  linkFilter?: JSONAPI.ShakeToReportCategory;
  spikes: JSONAPI.SpikeWord[];
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
        <th colSpan={3}>
          Trending words on{" "}
          {date ? formatISO(date, { representation: "date" }) : null}
        </th>
      </tr>
      <tr>
        <th>Spikiness</th>
        <th>Word</th>
        <th>Confirmed</th>
      </tr>
    </thead>
    <tbody>
      {spikes.map(spike => {
        const params = new URLSearchParams();
        if (linkFilter) {
          params.set("filter", linkFilter);
        }
        params.set("q", spike.word);
        return (
          <tr key={spike.word}>
            <td>{spike.score.toFixed(1)}</td>
            <td>
              <Link
                to={`/${language}/analysis?${encodeURLSearchParams(params)}`}
              >
                {spike.word}
              </Link>
            </td>
            <td className={styles.toggle}>
              <ConfirmButton spike={spike} />
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
