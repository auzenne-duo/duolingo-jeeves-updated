import * as React from "react";

import { canFitMenuAndContent } from "components/MenuDrawer";

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

export const initialState: State = {
  loading: false,
  showAside: false,
  showMenu: canFitMenuAndContent(),
};

export const reducer: React.Reducer<State, Action> = (state, action) => {
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

const AppStateContext = React.createContext<[State, React.Dispatch<Action>]>([
  initialState,
  () => {},
]);

export default AppStateContext;
