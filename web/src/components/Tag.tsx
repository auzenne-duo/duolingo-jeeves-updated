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
    className={cn(styles.tag, className, {
      [styles["priority-high"]]:
        isPriority &&
        ["high", "highest", "urgent"].includes(value.toLowerCase()),
      [styles["priority-low"]]:
        isPriority && ["low", "lowest"].includes(value.toLowerCase()),
      [styles["priority-medium"]]:
        isPriority && ["medium", "normal"].includes(value.toLowerCase()),
    })}
    title={value}
  >
    <span className={styles.value}>{text ?? value}</span>
  </span>
);

export default Tag;
