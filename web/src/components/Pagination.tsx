import type { LocationDescriptor } from "history";
import * as React from "react";
import { Button } from "web-ui/juicy";

import LinkButton from "components/LinkButton";
import styles from "components/Pagination.scss";

interface Props {
  nextLink?: LocationDescriptor | (() => void);
  prevLink?: LocationDescriptor | (() => void);
}

const Pagination = ({ nextLink, prevLink }: Props) => (
  <nav className={styles.wrap}>
    {prevLink ? (
      typeof prevLink === "function" ? (
        <Button onClick={prevLink} variant="outline">
          Previous
        </Button>
      ) : (
        <LinkButton to={prevLink} variant="outline">
          Previous
        </LinkButton>
      )
    ) : null}
    {nextLink ? (
      typeof nextLink === "function" ? (
        <Button className={styles.next} onClick={nextLink} variant="outline">
          Next
        </Button>
      ) : (
        <LinkButton className={styles.next} to={nextLink} variant="outline">
          Next
        </LinkButton>
      )
    ) : null}
  </nav>
);

export default Pagination;
