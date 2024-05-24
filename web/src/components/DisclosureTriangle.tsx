import cn from "classnames";
import React from "react";

import styles from "components/DisclosureTriangle.module.scss";

type Direction = "down" | "left" | "right" | "up";

interface Props {
  className?: string;
  direction: Direction;
}

const ROTATIONS: Record<Direction, number> = {
  down: 0,
  left: 90,
  right: 270,
  up: -180,
};

const DisclosureTriangle = ({ className, direction }: Props) => (
  <div
    className={cn(styles.wrap, className)}
    style={{
      transform: `rotate(${ROTATIONS[direction]}deg)`,
    }}
  >
    ▾
  </div>
);

export default DisclosureTriangle;
