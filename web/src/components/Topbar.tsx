import * as React from "react";
import { NavLink, Route, useHistory, useParams } from "react-router-dom";
import { Input } from "web-ui";

import { LanguageId } from "components/LanguagePicker";
import useSearchParams from "components/useSearchParams";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

const Topbar = () => {
  const history = useHistory();
  const { lang } = useParams<{ lang: LanguageId }>();
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  const [input, setInput] = React.useState(query);

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
          <img alt="Duolingo" className={styles.logo} src={imageLogo} />
        </NavLink>
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
      </nav>
    </div>
  );
};

export default Topbar;
