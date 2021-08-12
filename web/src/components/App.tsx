import * as React from "react";
import { Route, Switch } from "react-router-dom";

import MenuDrawer, { canFitMenuAndContent } from "components/MenuDrawer";
import Topbar from "components/Topbar";
import Analysis from "components/pages/Analysis";
import Dashboard from "components/pages/Dashboard";
import Discovery from "components/pages/Discovery";
import Spike from "components/pages/Spike";
import AppStateContext, {
  initialState,
  reducer,
} from "contexts/AppStateContext";
import styles from "styles/App.scss";
import track from "track";

const App = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);

  React.useEffect(() => {
    localStorage.setItem("searchHistory", JSON.stringify(state.searchHistory));
  }, [state.searchHistory]);

  React.useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (state.showMenu && !canFitMenuAndContent()) {
          dispatch({ type: "HIDE_MENU" });
        } else {
          dispatch({ type: "HIDE_ASIDE" });
        }
        e.preventDefault();
      } else if (e.key === "[") {
        dispatch({ type: "TOGGLE_MENU" });
        e.preventDefault();
      }
    };
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, [state.showMenu]);

  React.useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        track("jeeves_active_user");
      }
    };
    handleVisibilityChange();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return (
    <AppStateContext.Provider value={[state, dispatch]}>
      <Topbar />
      <div className={styles[`wrap${state.showAside ? "-shifted" : ""}`]}>
        <div className={styles.content}>
          <Switch>
            <Route path="/:lang/analysis">
              <Analysis />
            </Route>
            <Route path="/:lang/discovery">
              <Discovery />
            </Route>
            <Route path="/:lang/spike">
              <Spike />
            </Route>
            <Route>
              <Dashboard />
            </Route>
          </Switch>
        </div>
        <div className={styles.aside} id="aside" />
      </div>
      <MenuDrawer
        isOpen={state.showMenu}
        onRequestClose={() => dispatch({ type: "HIDE_MENU" })}
      />
    </AppStateContext.Provider>
  );
};

export default App;
