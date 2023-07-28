import * as React from "react";

import styles from "components/spike-detector/ExperimentsList.scss";

interface Props {
  experimentSpikes: JSONAPI.ExperimentSpike[];
}

const ExperimentsList = ({ experimentSpikes }: Props) => (
  <ul className={styles.ul}>
    {experimentSpikes
      .sort((a, b) => b.score - a.score)
      .map(experimentSpike => (
        <li key={experimentSpike.experiment}>
          <a
            href={`https://metrics.duolingo.com/experiments/${experimentSpike.experiment}`}
          >
            {experimentSpike.experiment}: {experimentSpike.score.toFixed(1)}
          </a>
        </li>
      ))}
  </ul>
);

export default ExperimentsList;
