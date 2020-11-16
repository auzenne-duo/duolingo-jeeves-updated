import cn from "classnames";
import { LocationDescriptor } from "history";
import * as React from "react";
import { Link } from "react-router-dom";
import { getButtonClassName } from "web-ui";

import styles from "styles/Pagination.scss";

interface Props {
  nextLink?: LocationDescriptor;
  prevLink?: LocationDescriptor;
}

const Pagination: React.FC<Props> = ({ nextLink, prevLink }) => (
  <nav className={styles.wrap}>
    {prevLink ? (
      <Link className={getButtonClassName({ variant: "stroke" })} to={prevLink}>
        Previous
      </Link>
    ) : null}
    {nextLink ? (
      <Link
        className={cn(getButtonClassName({ variant: "stroke" }), styles.next)}
        to={nextLink}
      >
        Next
      </Link>
    ) : null}
  </nav>
);

export default Pagination;
