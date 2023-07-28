import * as React from "react";
import { Button } from "web-ui";

import styles from "components/Hamburger.scss";

interface Props {
  isOpen: boolean;
  onClick?: React.MouseEventHandler;
}

const Hamburger = ({ isOpen, onClick }: Props) => (
  <Button
    className={styles[`hamburger${isOpen ? "-open" : ""}`]}
    onClick={onClick}
    onMouseUp={e => {
      // Don't call the native listener on document that `useClickOutside` registers.
      e.stopPropagation();
    }}
  >
    <span className={styles.bar} />
    <span className={styles.bar} />
    <span className={styles.bar} />
  </Button>
);

export default Hamburger;
