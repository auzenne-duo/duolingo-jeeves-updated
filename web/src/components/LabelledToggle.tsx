import * as React from "react";
import { Toggle } from "web-ui/juicy";

import cn from "classnames";
import styles from "components/LabelledToggle.module.scss";

export interface Props {
  checked: boolean;
  className?: string;
  onClick?: () => void;
  title: string;
}

const LabelledToggle = ({ checked, className, onClick, title }: Props) => (
  <div className={cn(styles.wrap, className)}>
    <span className={styles.label}>{title}</span>
    <Toggle checked={checked} className={styles.toggle} onClick={onClick} />
  </div>
);

export default LabelledToggle;
