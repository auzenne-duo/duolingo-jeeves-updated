import * as React from "react";
import {
  NavLink,
  Route,
  Switch,
  useHistory,
  useParams,
} from "react-router-dom";
import { Input, LoadingDots, Select } from "web-ui";

import { LanguageId } from "components/LanguagePicker";
import useSearchParams from "components/useSearchParams";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

interface Props {
  isLoading: boolean;
}

const Topbar: React.FC<Props> = ({ isLoading }) => {
  const history = useHistory();
  const { lang } = useParams<{ lang: LanguageId }>();
  const search = useSearchParams();

  const filter = search.get("filter");
  const query = search.get("q") ?? "";

  const [input, setInput] = React.useState(query);

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    history.push({
      ...location,
      search: `filter=${encodeURIComponent(e.target.value)}`,
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    history.push({
      ...location,
      search: `q=${encodeURIComponent(input)}`,
    });
  };

  React.useEffect(() => {
    // If the query is updated without using the input,
    // sync the input with the new URL.
    setInput(query);
  }, [query]);

  return (
    <div className={styles.container}>
      <nav className={styles.wrap}>
        <NavLink className={styles["logo-link"]} to={`/${lang}`}>
          <img
            alt="Duolingo"
            className={styles[`logo${isLoading ? "-invisible" : ""}`]}
            src={imageLogo}
          />
          {isLoading ? <LoadingDots type="button" /> : null}
        </NavLink>
        <Switch>
          <Route path="/:lang/analysis">
            <form className={styles.search} onSubmit={handleSubmit}>
              <Input
                onChange={e => setInput(e.target.value)}
                placeholder="Search"
                type="search"
                value={input}
              />
            </form>
          </Route>
          <Route path="/:lang/discovery">
            <Select
              className={styles.filter}
              onChange={handleFilterChange}
              options={[
                { text: "All sources", value: "all" },
                { text: "Beta program", value: "beta" },
              ]}
              value={filter ?? "beta"}
            />
          </Route>
          <Route path="/:lang/spike">
            <Select
              className={styles.filter}
              onChange={handleFilterChange}
              options={[
                { text: "All sources", value: "ALL_SPIKES" },
                { text: "All dogfooding", value: "ALL_STR_SPIKES" },
                { text: "External dogfooding", value: "EXTERNAL_STR_SPIKES" },
                {
                  text: "External non-dogfooding",
                  value: "EXTERNAL_NON_STR_SPIKES",
                },
                { text: "Internal dogfooding", value: "INTERNAL_STR_SPIKES" },
                {
                  text: "Internal non-dogfooding",
                  value: "INTERNAL_NON_STR_SPIKES",
                },
                { text: "Non-dogfooding", value: "ALL_NON_STR_SPIKES" },
              ]}
              value={filter ?? "ALL_SPIKES"}
            />
          </Route>
        </Switch>
      </nav>
    </div>
  );
};

export default Topbar;
