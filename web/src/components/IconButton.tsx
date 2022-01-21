import cn from "classnames";
import * as React from "react";
import { Button } from "web-ui";

import styles from "styles/IconButton.scss";

interface Props {
  className?: string;
  icon: string;
  onClick?: React.MouseEventHandler;
  title?: string;
}

const IconButton = ({ className, icon, onClick, title }: Props) => (
  <Button
    className={cn(styles.button, className)}
    onClick={onClick}
    title={title}
  >
    <img className={styles.icon} src={icon} />
  </Button>
);

export default IconButton;
