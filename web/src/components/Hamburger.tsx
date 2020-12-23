import * as React from "react";
import { Button } from "web-ui";

import styles from "styles/Hamburger.scss";

interface Props {
  isOpen: boolean;
  onClick?: React.MouseEventHandler;
}

const Hamburger: React.FC<Props> = ({ isOpen, onClick }) => (
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
