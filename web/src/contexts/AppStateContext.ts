import * as React from "react";

import type { ReportIssueResult } from "api/shakira";
import { canFitMenuAndContent } from "components/MenuDrawer";

type Action =
  | { type: "ESCAPE" }
  | { type: "HIDE_ASIDE" }
  | { type: "HIDE_MENU" }
  | { type: "LIGHTBOX"; url: string }
  | { type: "LOADED" }
  | { type: "LOADING" }
  | { issue: ReportedIssue; type: "REPORTED_ISSUE" }
  | { context: "nlp" | "tickets"; query: string; type: "SEARCH" }
  | { type: "SHOW_ASIDE" }
  | { type: "SHOW_MENU" }
  | { type: "TOGGLE_ASIDE" }
  | { type: "TOGGLE_MENU" };

interface ReportedIssue {
  jeeves_uid: string;
  result: ReportIssueResult;
  summary: string;
}

interface State {
  lightboxUrl?: string;
  loading: boolean;
  /** Keep a list of issues reported to Jira/Slack since the page was last refreshed. */
  reportedIssues: ReportedIssue[];
  searchHistory: string[];
  searchHistoryNLP: string[];
  showAside: boolean;
  showMenu: boolean;
}

export const initialState: State = {
  loading: false,
  reportedIssues: [],
  searchHistory: JSON.parse(localStorage.getItem("searchHistory") ?? "[]"),
  searchHistoryNLP: JSON.parse(
    localStorage.getItem("searchHistoryNLP") ?? "[]",
  ),
  showAside: false,
  showMenu: canFitMenuAndContent(),
};

export const reducer: React.Reducer<State, Action> = (state, action) => {
  switch (action.type) {
    case "ESCAPE":
      return state.lightboxUrl
        ? { ...state, lightboxUrl: undefined }
        : state.showMenu && !canFitMenuAndContent()
        ? { ...state, showMenu: false }
        : { ...state, showAside: false };
    case "HIDE_ASIDE":
      return { ...state, showAside: false };
    case "HIDE_MENU":
      return { ...state, showMenu: false };
    case "LIGHTBOX":
      return { ...state, lightboxUrl: action.url };
    case "LOADED":
      return { ...state, loading: false };
    case "LOADING":
      return { ...state, loading: true };
    case "REPORTED_ISSUE":
      return {
        ...state,
        reportedIssues: [
          ...state.reportedIssues.filter(
            i => i.jeeves_uid !== action.issue.jeeves_uid,
          ),
          action.issue,
        ],
      };
    case "SEARCH":
      if (action.query.trim() === "") {
        return state;
      }
      if (action.context === "nlp") {
        return {
          ...state,
          searchHistoryNLP: [
            action.query.trim(),
            ...state.searchHistoryNLP
              .filter(q => q !== action.query.trim())
              .slice(0, 20),
          ],
        };
      }
      return {
        ...state,
        searchHistory: [
          action.query.trim(),
          ...state.searchHistory
            .filter(q => q !== action.query.trim())
            .slice(0, 20),
        ],
      };
    case "SHOW_ASIDE":
      return { ...state, showAside: true };
    case "SHOW_MENU":
      return { ...state, showMenu: true };
    case "TOGGLE_ASIDE":
      return { ...state, showAside: !state.showAside };
    case "TOGGLE_MENU":
      return { ...state, showMenu: !state.showMenu };
  }
  return state;
};

const AppStateContext = React.createContext<[State, React.Dispatch<Action>]>([
  initialState,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  () => {},
]);

export default AppStateContext;
