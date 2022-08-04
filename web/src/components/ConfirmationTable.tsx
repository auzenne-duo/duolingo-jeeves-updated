import React from "react";

import Table from "components/Table";
import styles from "styles/ConfirmationTable.scss";

interface Props {
  confirmationStats: JSONAPI.ConfirmationStats;
}

const ConfirmationTable = ({ confirmationStats }: Props) => (
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
      {Object.entries(confirmationStats).map(([date, value]) => {
        const percent = Math.round((100 * value.confirmed) / value.total);
        return (
          <tr key={date}>
            <td>{date}</td>
            <td>{value.total}</td>
            <td>{value.confirmed}</td>
            <td>{percent}%</td>
          </tr>
        );
      })}
    </tbody>
  </Table>
);

export default ConfirmationTable;
