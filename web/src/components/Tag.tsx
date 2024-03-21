import * as React from "react";

import cn from "classnames";
import styles from "components/Tag.module.scss";
import imageLink from "images/link.svg";

interface Props {
  className?: string;
  isPriority?: boolean;
  showLinkIcon?: boolean;
  /** Optional display text to show instead of the value. */
  text?: string;
  value: string;
}

const Tag = ({ className, isPriority, showLinkIcon, text, value }: Props) => (
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
    {showLinkIcon ? (
      <img alt="" className={styles.icon} src={imageLink} />
    ) : null}
  </span>
);

export default Tag;
