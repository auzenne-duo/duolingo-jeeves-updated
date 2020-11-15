import * as React from "react";
import { Route, Switch } from "react-router-dom";

import Sidebar from "components/Sidebar";
import Topbar from "components/Topbar";
import Analysis from "components/pages/Analysis";
import Dashboard from "components/pages/Dashboard";
import Spike from "components/pages/Spike";
import styles from "styles/App.scss";

const App = () => (
  <>
    <Topbar />
    <div className={styles.main}>
      <div className={styles.sidebar}>
        <Sidebar />
      </div>
      <div className={styles.content}>
        <Switch>
          <Route path="/:lang/analysis">
            <Analysis />
          </Route>
          <Route path="/:lang/spike">
            <Spike />
          </Route>
          <Route>
            <Dashboard />
          </Route>
        </Switch>
      </div>
    </div>
  </>
);

export default App;
