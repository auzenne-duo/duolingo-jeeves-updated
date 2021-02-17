import cn from "classnames";
import * as React from "react";

import styles from "styles/Tag.scss";

interface Props {
  className?: string;
  isPriority?: boolean;
  /** Optional display text to show instead of the value. */
  text?: string;
  value: string;
}

const Tag: React.FC<Props> = ({ className, isPriority, text, value }) => (
  <span
    className={cn(styles[`tag${isPriority ? "-priority" : ""}`], className)}
    title={value}
  >
    <span className={styles.value}>{text ?? value}</span>
  </span>
);

export default Tag;
