import * as React from "react";
import { DimmedOverlay, useFade } from "web-ui";

import styles from "components/Lightbox.module.scss";
import AppStateContext from "contexts/AppStateContext";

const Lightbox = () => {
  const [state, dispatch] = React.useContext(AppStateContext);

  const ref = React.useRef<HTMLDivElement>(null);

  const isVisible = state.lightboxUrl !== undefined;

  useFade(ref, { isVisible });

  return (
    <div
      className={isVisible ? styles["wrap-visible"] : styles.wrap}
      onClick={() => dispatch({ type: "ESCAPE" })}
      ref={ref}
    >
      <DimmedOverlay />
      <img
        alt=""
        className={styles.image}
        key={state.lightboxUrl}
        src={state.lightboxUrl}
      />
    </div>
  );
};

export default Lightbox;
