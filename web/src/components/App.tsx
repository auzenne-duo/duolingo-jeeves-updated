import {
  QueryClient,
  QueryClientProvider,
  useIsFetching,
  useQuery,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import * as React from "react";
import { Route, Switch } from "react-router-dom";
import { ThemeProvider } from "web-ui";

import { getLoggedIn } from "api/user";
import styles from "components/App.scss";
import Lightbox from "components/Lightbox";
import MenuDrawer from "components/MenuDrawer";
import Topbar from "components/Topbar";
import Dashboard from "components/dashboard/Dashboard";
import GPTSearch from "components/gpt-search/GPTSearch";
import IssueDiscovery from "components/issue-discovery/IssueDiscovery";
import QualityReport from "components/quality-report/QualityReport";
import SentimentSearch from "components/sentiment-search/SentimentSearch";
import SpikeDetector from "components/spike-detector/SpikeDetector";
import SpikeStats from "components/spike-stats/SpikeStats";
import TimeSeriesAnalyzer from "components/time-series-analyzer/TimeSeriesAnalyzer";
import usePage from "components/usePage";
import usePageLanguage from "components/usePageLanguage";
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
  const isFetching = useIsFetching();

  const [state, dispatch] = React.useContext(AppStateContext);
  const [trackedSearches, setTrackedSearches] = React.useState<string[]>([]);

  const language = usePageLanguage();
  const page = usePage();
  const user = useQuery(["user"], () => getLoggedIn()).data;
  const isAdmin = user?.roles?.includes("admin") ?? false;

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
    localStorage.setItem(
      "searchHistoryGPT",
      JSON.stringify(state.searchHistoryGPT),
    );
  }, [state.searchHistoryGPT]);

  React.useEffect(() => {
    const trackableSearches = state.searches.filter(
      s => !trackedSearches.includes(s.id),
    );
    trackableSearches.forEach(s => {
      track("jeeves_search", {
        id: s.id,
        is_admin: isAdmin,
        jeeves_answer: s.answer,
        language: s.language,
        num_results: s.numResults,
        page: s.page,
        query: s.searchString,
        query_time_ms: s.endTime - s.startTime,
        query_type: s.queryType,
        user_agent: navigator.userAgent,
        // Convert minutes to hours and invert the sign to match how we track utc_offset
        utc_offset: new Date().getTimezoneOffset() / -60,
      });
    });
    if (trackableSearches.length) {
      setTrackedSearches(value => [
        ...value,
        ...trackableSearches.map(s => s.id),
      ]);
    }
  }, [isAdmin, state.searches, trackedSearches]);

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
        track("jeeves_active_user", {
          is_admin: isAdmin,
          language,
          page,
          user_agent: navigator.userAgent,
          // Convert minutes to hours and invert the sign to match how we track utc_offset
          utc_offset: new Date().getTimezoneOffset() / -60,
        });
      }
    };
    handleVisibilityChange();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isAdmin, language, page]);

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
                <Route path="/:lang/quality-report">
                  <QualityReport />
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
