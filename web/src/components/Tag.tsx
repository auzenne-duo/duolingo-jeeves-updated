import * as React from "react";

import cn from "classnames";
import styles from "components/Tag.scss";

interface Props {
  className?: string;
  isPriority?: boolean;
  /** Optional display text to show instead of the value. */
  text?: string;
  value: string;
}

const Tag = ({ className, isPriority, text, value }: Props) => (
  <span
    className={cn(styles[`tag${isPriority ? "-priority" : ""}`], className)}
    title={value}
  >
    <span className={styles.value}>{text ?? value}</span>
  </span>
);

export default Tag;
