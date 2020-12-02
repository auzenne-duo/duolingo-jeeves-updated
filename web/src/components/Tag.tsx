import cn from "classnames";
import * as React from "react";

import styles from "styles/Tag.scss";

interface Props {
  className?: string;
  isPriority?: boolean;
  value: string;
}

const Tag: React.FC<Props> = ({ className, isPriority, value }) => (
  <span
    className={cn(styles[`tag${isPriority ? "-priority" : ""}`], className)}
  >
    {value}
  </span>
);

export default Tag;
