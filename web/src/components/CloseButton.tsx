import * as React from "react";
import { Button } from "web-ui";

import imageClose from "images/x.svg";
import styles from "styles/CloseButton.scss";

interface Props {
  onClick?: React.MouseEventHandler;
}

const CloseButton: React.FC<Props> = ({ onClick }) => (
  <Button className={styles.close} onClick={onClick}>
    <img src={imageClose} />
  </Button>
);

export default CloseButton;
