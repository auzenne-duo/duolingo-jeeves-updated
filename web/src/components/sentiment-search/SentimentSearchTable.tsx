import * as React from "react";

import { getPaginationString } from "../../util";
import Pagination from "components/Pagination";
import Table from "components/Table";
import styles from "components/sentiment-search/SentimentSearchTable.scss";

const RESULTS_PER_PAGE = 30;

interface Props {
  docs: JSONAPI.SentimentSearchResult[];
}

const SentimentSearchTable = ({ docs }: Props) => {
  const [currentPage, setCurrentPage] = React.useState(1);
  const totalPages = Math.ceil(docs.length / RESULTS_PER_PAGE);
  const indexOfLastDoc = currentPage * RESULTS_PER_PAGE;
  const indexOfFirstDoc = indexOfLastDoc - RESULTS_PER_PAGE;
  const currentDocs = docs.slice(indexOfFirstDoc, indexOfLastDoc);

  const handleNextPage = () => {
    setCurrentPage(prevPage => Math.min(prevPage + 1, totalPages));
  };

  const handlePrevPage = () => {
    setCurrentPage(prevPage => Math.max(prevPage - 1, 1));
  };

  return (
    <>
      <Table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.document}>Document</th>
            <th>Text</th>
          </tr>
        </thead>
        <tbody>
          {currentDocs.map(d => (
            <tr key={d.uid}>
              <td className={styles.document}>
                <b>Source:</b> {d.origin}
                <br />
                <b>Date:</b> {new Date(d.datetime).toLocaleString()}
                <br />
                <b>Label:</b> {d.label === "none" ? "neutral" : d.label}
              </td>
              <td className={styles.cell}>
                {d.original_text.title && (
                  <div className={styles.title}>
                    Title: {d.original_text.title}
                  </div>
                )}
                <div className={styles.body}>{d.original_text.body}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
      <div className={styles.pagination}>
        {getPaginationString({
          offset: (currentPage - 1) * RESULTS_PER_PAGE,
          perPage: RESULTS_PER_PAGE,
          total: docs.length,
        })}
      </div>
      {currentPage > 1 || currentPage < totalPages ? (
        <Pagination
          nextLink={currentPage < totalPages ? handleNextPage : undefined}
          prevLink={currentPage > 1 ? handlePrevPage : undefined}
        />
      ) : null}
    </>
  );
};

export default SentimentSearchTable;
