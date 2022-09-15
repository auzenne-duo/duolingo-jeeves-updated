import * as _ from "lodash";
import React from "react";

import DisclosureTriangle from "components/DisclosureTriangle";
import Table from "components/Table";
import styles from "styles/SortTable.scss";

interface Props<T> {
  columns: Column<T>[];
  data: T[];
}

export interface Column<T> {
  getCell: (n: T) => React.ReactNode;
  getValue: (n: T) => number | string;
  header: string;
}

enum SortStatus {
  Ascending = "ascending",
  Descending = "descending",
}

const SortTable = <T,>({ columns, data }: Props<T>) => {
  const [sortedData, setSortedData] = React.useState(data);
  const [sortColumnIndex, setSortColumnIndex] = React.useState(-1);
  const [sortStatus, setSortStatus] = React.useState<SortStatus>(
    SortStatus.Ascending,
  );

  // Reset sort whenever underlying data changes.
  React.useLayoutEffect(() => {
    setSortedData(data);
    setSortColumnIndex(-1);
    setSortStatus(SortStatus.Ascending);
  }, [data]);

  return (
    <Table className={styles.widetable}>
      <thead>
        <tr>
          {columns.map((c, i) => {
            const columnSortStatus =
              sortColumnIndex === i ? sortStatus : SortStatus.Ascending;

            const handleClick = () => {
              const nextSortStatus =
                columnSortStatus === SortStatus.Ascending
                  ? SortStatus.Descending
                  : SortStatus.Ascending;
              const nextSortedData = _.sortBy<T>(sortedData, c.getValue);

              if (nextSortStatus === SortStatus.Descending) {
                nextSortedData.reverse();
              }

              setSortColumnIndex(i);
              setSortStatus(nextSortStatus);
              setSortedData(nextSortedData);
            };

            return (
              <th
                className={styles.clickable}
                key={c.header}
                onClick={handleClick}
              >
                {c.header}
                <DisclosureTriangle
                  className={styles.triangle}
                  direction={
                    columnSortStatus === SortStatus.Ascending ? "down" : "up"
                  }
                />
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>
        {sortedData.map((e, i) => (
          <tr key={`${i}`}>
            {columns.map((c, j) => (
              <td key={`${j}`}>{c.getCell(e)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

export default SortTable;
