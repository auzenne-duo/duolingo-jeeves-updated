import type { LocationDescriptor } from "history";
import * as React from "react";
import { Link } from "react-router-dom";
import { Button, getButtonClassName } from "web-ui";

import cn from "classnames";
import styles from "styles/Pagination.scss";

interface Props {
  nextLink?: LocationDescriptor | (() => void);
  prevLink?: LocationDescriptor | (() => void);
}

const Pagination = ({ nextLink, prevLink }: Props) => (
  <nav className={styles.wrap}>
    {prevLink ? (
      typeof prevLink === "function" ? (
        <Button onClick={prevLink} variant="stroke">
          Previous
        </Button>
      ) : (
        <Link
          className={getButtonClassName({ variant: "stroke" })}
          to={prevLink}
        >
          Previous
        </Link>
      )
    ) : null}
    {nextLink ? (
      typeof nextLink === "function" ? (
        <Button className={styles.next} onClick={nextLink} variant="stroke">
          Previous
        </Button>
      ) : (
        <Link
          className={cn(getButtonClassName({ variant: "stroke" }), styles.next)}
          to={nextLink}
        >
          Next
        </Link>
      )
    ) : null}
  </nav>
);

export default Pagination;
