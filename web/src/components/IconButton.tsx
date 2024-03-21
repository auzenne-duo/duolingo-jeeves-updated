import * as React from "react";
import { LegacyButton } from "web-ui/legacy";

import cn from "classnames";
import styles from "components/IconButton.module.scss";

interface Props {
  className?: string;
  icon: string;
  onClick?: React.MouseEventHandler;
  title?: string;
}

const IconButton = ({ className, icon, onClick, title }: Props) => (
  <LegacyButton
    className={cn(styles.button, className)}
    onClick={onClick}
    title={title}
  >
    <img className={styles.icon} src={icon} />
  </LegacyButton>
);

export default IconButton;
