import * as React from "react";
import { Toggle } from "web-ui";

import cn from "classnames";
import styles from "styles/LabelledToggle.scss";

export interface Props {
  checked: boolean;
  className?: string;
  onChange?: () => void;
  title: string;
}

const LabelledToggle = ({ checked, className, onChange, title }: Props) => (
  <div className={cn(styles.wrap, className)}>
    <span className={styles.label}>{title}</span>
    <Toggle checked={checked} className={styles.toggle} onChange={onChange} />
  </div>
);

export default LabelledToggle;
