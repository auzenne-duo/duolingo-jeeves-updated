import * as React from "react";
import { DimmedOverlay } from "web-ui";

import AppStateContext from "contexts/AppStateContext";
import styles from "styles/Lightbox.scss";

const Lightbox = () => {
  const [state, dispatch] = React.useContext(AppStateContext);
  return state.lightboxUrl ? (
    <div className={styles.wrap} onClick={() => dispatch({ type: "ESCAPE" })}>
      <DimmedOverlay />
      <img alt="" className={styles.image} src={state.lightboxUrl} />
    </div>
  ) : null;
};

export default Lightbox;
