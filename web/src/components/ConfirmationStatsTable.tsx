import React from "react";

import Table from "components/Table";
import styles from "styles/ConfirmationStatsTable.scss";

interface Props {
  spikeStats: JSONAPI.SpikeStats;
}

const ConfirmationStatsTable = ({ spikeStats }: Props) => (
  <Table className={styles.table}>
    <thead>
      <tr>
        <th>Month</th>
        <th>Num spikes</th>
        <th>Num confirmed</th>
        <th>Percent confirmed</th>
      </tr>
    </thead>
    <tbody>
      {spikeStats.month_count.map(value => {
        const percent = Math.round((100 * value.confirmed) / value.total);
        return (
          <tr key={value.date_str}>
            <td>{value.date_str}</td>
            <td>{value.total}</td>
            <td>{value.confirmed}</td>
            <td>{percent}%</td>
          </tr>
        );
      })}
    </tbody>
  </Table>
);

export default ConfirmationStatsTable;
