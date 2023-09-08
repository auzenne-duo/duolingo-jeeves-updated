import * as React from "react";
import { v4 as uuidv4 } from "uuid";

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
  | {
      language?: JSONAPI.LanguageId;
      page?: string;
      queryType: string;
      searchString: string;
      timestamp: number;
      type: "SEARCH_BEGIN";
    }
  | {
      answer?: string;
      numResults: number;
      timestamp: number;
      type: "SEARCH_END";
    }
  | { type: "SHOW_ASIDE" }
  | { type: "SHOW_MENU" }
  | { type: "TOGGLE_ASIDE" }
  | { type: "TOGGLE_MENU" };

interface ReportedIssue {
  jeeves_uid: string;
  result: ReportIssueResult;
  summary: string;
}

interface SearchContext {
  id: string;
  language?: JSONAPI.LanguageId;
  page?: string;
  queryType: string;
  searchString: string;
  startTime: number;
}

interface Search extends SearchContext {
  answer?: string;
  endTime: number;
  numResults: number;
}

interface State {
  lightboxUrl?: string;
  loading: boolean;
  pendingSearch?: SearchContext;
  /** Keep a list of issues reported to Jira/Slack since the page was last refreshed. */
  reportedIssues: ReportedIssue[];
  searchHistory: string[];
  searchHistoryGPT: string[];
  searches: Search[];
  showAside: boolean;
  showMenu: boolean;
}

export const initialState: State = {
  loading: false,
  pendingSearch: undefined,
  reportedIssues: [],
  searchHistory: JSON.parse(localStorage.getItem("searchHistory") ?? "[]"),
  searchHistoryGPT: JSON.parse(
    localStorage.getItem("searchHistoryGPT") ?? "[]",
  ),
  searches: [],
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
    case "SEARCH_BEGIN": {
      const query = action.searchString.trim();
      let updatedHistory = {};
      if (query) {
        const key =
          action.queryType === "gpt-search" ||
          action.queryType === "sentiment-search"
            ? "searchHistoryGPT"
            : "searchHistory";
        updatedHistory = {
          [key]: [query, ...state[key].filter(q => q !== query).slice(0, 20)],
        };
      }
      return {
        ...state,
        ...updatedHistory,
        pendingSearch: {
          id: uuidv4(),
          language: action.language,
          page: action.page,
          queryType: action.queryType,
          searchString: action.searchString,
          startTime: action.timestamp,
        },
      };
    }
    case "SEARCH_END": {
      const pending = state.pendingSearch;
      if (!pending) {
        return state;
      }
      return {
        ...state,
        pendingSearch: undefined,
        searches: [
          ...state.searches,
          {
            ...pending,
            answer: action.answer,
            endTime: action.timestamp,
            numResults: action.numResults,
          },
        ],
      };
    }
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
