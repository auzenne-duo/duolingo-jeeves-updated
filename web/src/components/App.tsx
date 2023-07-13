import {
  QueryClient,
  QueryClientProvider,
  useIsFetching,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import * as React from "react";
import { Route, Switch } from "react-router-dom";
import { ThemeProvider } from "web-ui";

import Lightbox from "components/Lightbox";
import MenuDrawer from "components/MenuDrawer";
import Topbar from "components/Topbar";
import Analysis from "components/pages/Analysis";
import Dashboard from "components/pages/Dashboard";
import Discovery from "components/pages/Discovery";
import GPTSearch from "components/pages/GPTSearch";
import Spike from "components/pages/Spike";
import SpikeStats from "components/pages/SpikeStats";
import AppStateContext, {
  initialState,
  reducer,
} from "contexts/AppStateContext";
import styles from "styles/App.scss";
import track from "track";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 3600000, // 1h
    },
  },
});

const AppProvider = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);
  return (
    <AppStateContext.Provider value={[state, dispatch]}>
      <QueryClientProvider client={queryClient}>
        <App />
        {process.env.NODE_ENV === "development" ? (
          // The devtools are still included in the production build but
          // that shouldn't be a problem for internal tools.
          <ReactQueryDevtools initialIsOpen={false} />
        ) : null}
      </QueryClientProvider>
    </AppStateContext.Provider>
  );
};

const App = () => {
  const [state, dispatch] = React.useContext(AppStateContext);
  const isFetching = useIsFetching();

  React.useEffect(() => {
    if (isFetching) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
    return undefined;
  }, [dispatch, isFetching]);

  React.useEffect(() => {
    localStorage.setItem("searchHistory", JSON.stringify(state.searchHistory));
  }, [state.searchHistory]);

  React.useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        dispatch({ type: "ESCAPE" });
        e.preventDefault();
      } else if (e.key === "[") {
        dispatch({ type: "TOGGLE_MENU" });
        e.preventDefault();
      }
    };
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, [dispatch]);

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
    <ThemeProvider theme="light">
      <AppStateContext.Provider value={[state, dispatch]}>
        <QueryClientProvider client={queryClient}>
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
                <Route path="/:lang/gpt-search">
                  <GPTSearch />
                </Route>
                <Route path="/:lang/spike">
                  <Spike />
                </Route>
                <Route path="/:lang/spike-stats">
                  <SpikeStats />
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
          <Lightbox />
        </QueryClientProvider>
      </AppStateContext.Provider>
    </ThemeProvider>
  );
};

export default AppProvider;
