import * as React from "react";
import { Route, Switch } from "react-router-dom";

import MenuDrawer, { canFitMenuAndContent } from "components/MenuDrawer";
import Topbar from "components/Topbar";
import Analysis from "components/pages/Analysis";
import Dashboard from "components/pages/Dashboard";
import Discovery from "components/pages/Discovery";
import Spike from "components/pages/Spike";
import styles from "styles/App.scss";

type Action =
  | { type: "HIDE_ASIDE" }
  | { type: "HIDE_MENU" }
  | { type: "LOADED" }
  | { type: "LOADING" }
  | { type: "SHOW_ASIDE" }
  | { type: "SHOW_MENU" }
  | { type: "TOGGLE_ASIDE" }
  | { type: "TOGGLE_MENU" };

interface State {
  loading: boolean;
  showAside: boolean;
  showMenu: boolean;
}

export const AppDispatch = React.createContext<React.Dispatch<Action> | null>(
  null,
);

const appStateReducer: React.Reducer<State, Action> = (state, action) => {
  switch (action.type) {
    case "HIDE_ASIDE":
      return { ...state, showAside: false };
    case "HIDE_MENU":
      return { ...state, showMenu: false };
    case "LOADED":
      return { ...state, loading: false };
    case "LOADING":
      return { ...state, loading: true };
    case "SHOW_ASIDE":
      return { ...state, showAside: true };
    case "SHOW_MENU":
      return { ...state, showMenu: true };
    case "TOGGLE_ASIDE":
      return { ...state, showAside: !state.showAside };
    case "TOGGLE_MENU":
      return { ...state, showMenu: !state.showMenu };
  }
};

const App = () => {
  const [state, dispatch] = React.useReducer(appStateReducer, {
    loading: false,
    showAside: false,
    showMenu: canFitMenuAndContent(),
  });

  React.useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (state.showMenu && !canFitMenuAndContent()) {
          dispatch({ type: "HIDE_MENU" });
        } else {
          dispatch({ type: "HIDE_ASIDE" });
        }
      } else if (e.key === "[") {
        dispatch({ type: "TOGGLE_MENU" });
      }
    };
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, [state.showMenu]);

  return (
    <AppDispatch.Provider value={dispatch}>
      <Topbar isLoading={state.loading} showMenu={state.showMenu} />
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
    </AppDispatch.Provider>
  );
};

export default App;
