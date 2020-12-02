import * as React from "react";
import { Route, Switch } from "react-router-dom";

import Sidebar from "components/Sidebar";
import Topbar from "components/Topbar";
import Analysis from "components/pages/Analysis";
import Dashboard from "components/pages/Dashboard";
import Discovery from "components/pages/Discovery";
import Spike from "components/pages/Spike";
import styles from "styles/App.scss";

type Action =
  | { type: "LOADED" }
  | { type: "LOADING" }
  | { type: "SHIFT" }
  | { type: "UNSHIFT" };

interface State {
  loading: boolean;
  shifted: boolean;
}

export const AppDispatch = React.createContext<React.Dispatch<Action> | null>(
  null,
);

const appStateReducer: React.Reducer<State, Action> = (state, action) => {
  switch (action.type) {
    case "LOADED":
      return { ...state, loading: false };
    case "LOADING":
      return { ...state, loading: true };
    case "SHIFT":
      return { ...state, shifted: true };
    case "UNSHIFT":
      return { ...state, shifted: false };
  }
};

const App = () => {
  const [state, dispatch] = React.useReducer(appStateReducer, {
    loading: false,
    shifted: false,
  });

  React.useLayoutEffect(() => {
    document.documentElement.style.setProperty(
      "--scrollbar-width",
      `${window.innerWidth - document.documentElement.clientWidth}px`,
    );
  }, []);

  return (
    <AppDispatch.Provider value={dispatch}>
      <Topbar isLoading={state.loading} />
      <div className={styles.wrap}>
        <div className={styles[`main${state.shifted ? "-shifted" : ""}`]}>
          <div className={styles.sidebar}>
            <Sidebar />
          </div>
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
          <div className={styles["sidebar-right"]} id="aside" />
        </div>
      </div>
    </AppDispatch.Provider>
  );
};

export default App;
