import "normalize.css";
import "web-ui/styles/fonts.scss";

import * as React from "react";
import { render } from "react-dom";
import {
  BrowserRouter as Router,
  Redirect,
  Route,
  Switch,
} from "react-router-dom";

import App from "components/App";
import "images/favicon.ico";
import "styles/index.scss";

const AppWithRouter = () => (
  <Router>
    <Switch>
      <Redirect exact={true} from="/" to="/en" />
      <Route path="/:lang">
        <App />
      </Route>
    </Switch>
  </Router>
);

render(<AppWithRouter />, document.getElementById("root"));
