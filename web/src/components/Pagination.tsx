import { LocationDescriptor } from "history";
import * as React from "react";
import { Link } from "react-router-dom";

import styles from "styles/Pagination.scss";

interface Props {
  nextLink?: LocationDescriptor;
  prevLink?: LocationDescriptor;
}

const Pagination: React.FC<Props> = ({ nextLink, prevLink }) => (
  <nav className={styles.wrap}>
    {prevLink ? (
      <Link className={styles.previous} to={prevLink}>
        Previous
      </Link>
    ) : null}
    {nextLink ? (
      <Link className={styles.next} to={nextLink}>
        Next
      </Link>
    ) : null}
  </nav>
);

export default Pagination;
