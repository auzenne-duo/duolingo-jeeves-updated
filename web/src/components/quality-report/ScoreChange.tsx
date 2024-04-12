import * as React from "react";

import styles from "components/quality-report/ScoreChange.module.scss";

interface Props {
  value: number;
}

const ScoreChange = ({ value }: Props) => (
  <span className={value >= 0 ? styles.positive : styles.negative}>
    {value > 0 ? "+" : ""}
    {value.toFixed(2)}
  </span>
);

export default ScoreChange;
