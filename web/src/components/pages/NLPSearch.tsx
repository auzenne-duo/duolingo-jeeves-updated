import { encodeURLSearchParams } from "util";

import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";
import { SearchSuggestions } from "web-ui";

import NLPSearchResults from "components/NLPSearchResults";
import type { SearchInputChangeEvent } from "components/SearchInput";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import styles from "styles/pages/NLPSearch.scss";

const NLPSearch = () => {
  useDocumentTitle("NLP Search");
  usePageView();

  const [{ searchHistory }] = React.useContext(AppStateContext);

  const history = useHistory();
  const location = useLocation();
  const search = useSearchParams();
  const query = search.get("q") ?? "";
  const value = "";
  const [input, setInput] = React.useState(query);
  const [, dispatch] = React.useContext(AppStateContext);
  const [shouldSubmit, setShouldSubmit] = React.useState(false);
  const items = React.useMemo(
    () => searchHistory.map(q => ({ text: q })),
    [searchHistory],
  );

  const handleSearchInputChange = (e: SearchInputChangeEvent) => {
    setInput(e.value);
  };

  const applyFilters = React.useCallback(
    (params: URLSearchParams) =>
      history.push({
        ...location,
        search: encodeURLSearchParams(params),
      }),
    [history, location],
  );

  React.useEffect(() => {
    // If the query is updated without using the input,
    // sync the input with the new URL.
    setInput(query);
  }, [query]);

  React.useEffect(() => {
    // Keep search history.
    dispatch({ query, type: "SEARCH_NLP" });
  }, [dispatch, query]);

  const handleSearchInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      setShouldSubmit(true);
      e.preventDefault();
    }
    // Do not trigger shortcuts.
    e.stopPropagation();
  };

  React.useEffect(() => {
    if (shouldSubmit) {
      const params = new URLSearchParams(location.search);
      params.delete("page");
      if (input) {
        params.set("q", input);
      } else {
        params.delete("q");
      }
      applyFilters(params);
      // Blur the search input. This also closes the dropdown.
      (document.activeElement as HTMLElement | null)?.blur?.();
      setShouldSubmit(false);
    }
  }, [applyFilters, input, location, shouldSubmit]);

  return (
    <>
      <SearchSuggestions
        className={styles.search}
        initialItems={10}
        items={items}
        onChange={handleSearchInputChange}
        onKeyDown={handleSearchInputKeyDown}
        placeholder="Search"
        query={value}
        value={input}
      />
      {query ? (
        <NLPSearchResults />
      ) : (
        <div className={styles.explanation}>
          <span className={styles.h1}>Jeeves NLP Search (Beta)</span>
          <span>
            Ask any question about Jeeves data in the search box and press
            &quot;enter&quot;.
          </span>
        </div>
      )}
    </>
  );
};

export default NLPSearch;
