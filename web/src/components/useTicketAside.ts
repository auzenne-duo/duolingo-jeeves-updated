import * as React from "react";

import AppStateContext from "contexts/AppStateContext";

const useTicketAside = (id: string | undefined) => {
  const [, dispatch] = React.useContext(AppStateContext);

  React.useEffect(() => {
    if (id) {
      dispatch?.({ type: "SHOW_ASIDE" });
      return () => {
        dispatch?.({ type: "HIDE_ASIDE" });
      };
    }
    return undefined;
  }, [dispatch, id]);

  React.useEffect(() => {
    if (id) {
      const handleKeydown = (e: KeyboardEvent) => {
        if (e.key === "]") {
          dispatch?.({ type: "TOGGLE_ASIDE" });
          e.preventDefault();
        }
      };
      document.addEventListener("keydown", handleKeydown);
      return () => document.removeEventListener("keydown", handleKeydown);
    }
    return undefined;
  }, [dispatch, id]);
};

export default useTicketAside;
