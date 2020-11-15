import * as React from "react";
import { LoadingDots } from "web-ui";

import styles from "styles/Loading.scss";

interface Props {
  type?: "table-cell";
}

const Loading: React.FC<Props> = ({ type }) => (
  <div className={styles[`wrap${type ? `-${type}` : ""}`]}>
    <LoadingDots type={type ? "button" : "screen-white"} />
  </div>
);

export default Loading;
