import "whatwg-fetch";

import "normalize.css";
import "web-ui/styles/fonts.scss";

import { ErrorBoundary, Provider } from "@rollbar/react";
import * as React from "react";
import { render } from "react-dom";
import {
  Redirect,
  Route,
  BrowserRouter as Router,
  Switch,
} from "react-router-dom";

import App from "components/App";
import "images/favicon.ico";
import "styles/index.scss";

const rollbarConfig = {
  accessToken: "58450d5ce0c24f97aa30aca8003ab95d",
  captureUncaught: true,
  captureUnhandledRejections: true,
  environment: process.env.NODE_ENV,
};

const AppWithRouter = () => (
  <Provider config={rollbarConfig}>
    <ErrorBoundary>
      <Router>
        <Switch>
          <Redirect exact={true} from="/" to="/en" />
          <Route path="/:lang">
            <App />
          </Route>
        </Switch>
      </Router>
    </ErrorBoundary>
  </Provider>
);

render(<AppWithRouter />, document.getElementById("root"));
