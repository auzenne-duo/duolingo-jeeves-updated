import * as React from "react";
import { LegacyButton } from "web-ui/legacy";

import styles from "components/Hamburger.module.scss";

interface Props {
  isOpen: boolean;
  onClick?: React.MouseEventHandler;
}

const Hamburger = ({ isOpen, onClick }: Props) => (
  <LegacyButton
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
  </LegacyButton>
);

export default Hamburger;
