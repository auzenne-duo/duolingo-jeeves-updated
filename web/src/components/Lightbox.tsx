import * as React from "react";
import { DimmedOverlay, Fade } from "web-ui";

import AppStateContext from "contexts/AppStateContext";
import styles from "styles/Lightbox.scss";

const Lightbox = () => {
  const [state, dispatch] = React.useContext(AppStateContext);
  return (
    <Fade isVisible={state.lightboxUrl !== undefined}>
      <div className={styles.wrap} onClick={() => dispatch({ type: "ESCAPE" })}>
        <DimmedOverlay />
        <img
          alt=""
          className={styles.image}
          key={state.lightboxUrl}
          src={state.lightboxUrl}
        />
      </div>
    </Fade>
  );
};

export default Lightbox;
