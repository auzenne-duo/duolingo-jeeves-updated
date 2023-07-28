import {
  QueryClient,
  QueryClientProvider,
  useIsFetching,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import * as React from "react";
import { Route, Switch } from "react-router-dom";
import { ThemeProvider } from "web-ui";

import styles from "components/App.scss";
import Lightbox from "components/Lightbox";
import MenuDrawer from "components/MenuDrawer";
import Topbar from "components/Topbar";
import Dashboard from "components/dashboard/Dashboard";
import GPTSearch from "components/gpt-search/GPTSearch";
import IssueDiscovery from "components/issue-discovery/IssueDiscovery";
import SentimentSearch from "components/sentiment-search/SentimentSearch";
import SpikeDetector from "components/spike-detector/SpikeDetector";
import SpikeStats from "components/spike-stats/SpikeStats";
import TimeSeriesAnalyzer from "components/time-series-analyzer/TimeSeriesAnalyzer";
import AppStateContext, {
  initialState,
  reducer,
} from "contexts/AppStateContext";
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
                  <TimeSeriesAnalyzer />
                </Route>
                <Route path="/:lang/discovery">
                  <IssueDiscovery />
                </Route>
                <Route path="/:lang/gpt-search">
                  <GPTSearch />
                </Route>
                <Route path="/:lang/sentiment-search">
                  <SentimentSearch />
                </Route>
                <Route path="/:lang/spike">
                  <SpikeDetector />
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
