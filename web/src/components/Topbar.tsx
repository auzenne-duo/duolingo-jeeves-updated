import { endOfDay } from "date-fns";
import * as React from "react";
import {
  NavLink,
  useHistory,
  useLocation,
  useParams,
  useRouteMatch,
} from "react-router-dom";
import { Input, LoadingDots, Select } from "web-ui";

import cn from "classnames";
import type { DateRangeChangeEvent } from "components/DateRangeInput";
import DateRangeInput from "components/DateRangeInput";
import Hamburger from "components/Hamburger";
import useDateRangeFilter from "components/useDateRangeFilter";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

const Topbar = () => {
  const { from, to } = useDateRangeFilter({
    daysAgo: useRouteMatch("/:lang/spike") ? 3 : 0,
  });
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const isAnalysisPage = useRouteMatch("/:lang/analysis");
  const isDiscoveryPage = useRouteMatch("/:lang/discovery");
  const isSpikePage = useRouteMatch("/:lang/spike");
  const search = useSearchParams();

  const filter = search.get("filter");
  const query = search.get("q") ?? "";

  const [state, dispatch] = React.useContext(AppStateContext);
  const [input, setInput] = React.useState(query);

  const applyFilters = (params: URLSearchParams) =>
    history.push({
      ...location,
      search: params.toString(),
    });

  const handleDateRangeChange = (e: DateRangeChangeEvent) => {
    const params = new URLSearchParams(location.search);
    params.delete("page");

    if (e.from) {
      params.set("from", e.from.toJSON());
    } else {
      params.delete("from");
    }

    if (e.to) {
      params.set("to", endOfDay(new Date(e.to)).toJSON());
    } else {
      params.delete("to");
    }

    applyFilters(params);
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const params = new URLSearchParams(location.search);
    params.delete("page");
    if (e.target.value) {
      params.set("filter", e.target.value);
    } else {
      params.delete("filter");
    }
    applyFilters(params);
  };

  const handleHamburgerClick = () => dispatch?.({ type: "TOGGLE_MENU" });

  const handleSearchInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      const params = new URLSearchParams(location.search);
      params.delete("page");
      if (input) {
        params.set("q", input);
      } else {
        params.delete("q");
      }
      applyFilters(params);
      e.preventDefault();
    }
    // Do not trigger shortcuts.
    e.stopPropagation();
  };

  React.useEffect(() => {
    // If the query is updated without using the input,
    // sync the input with the new URL.
    setInput(query);
  }, [query]);

  React.useEffect(() => {
    // Keep search history.
    dispatch({ query, type: "SEARCH" });
  }, [query]);

  return (
    <div className={cn(styles.wrap, { [styles.loading]: state.loading })}>
      <Hamburger isOpen={state.showMenu} onClick={handleHamburgerClick} />
      <NavLink className={styles["logo-link"]} to={`/${lang}`}>
        <img alt="Duolingo Jeeves" className={styles.logo} src={imageLogo} />
        {state.loading ? <LoadingDots type="button" /> : null}
      </NavLink>
      <div
        className={
          styles[
            `filters${
              isAnalysisPage
                ? "-analysis"
                : isDiscoveryPage
                ? "-discovery"
                : isSpikePage
                ? "-spike"
                : ""
            }`
          ]
        }
      >
        {isAnalysisPage || isDiscoveryPage ? (
          <>
            <Input
              autoComplete="off"
              className={styles.search}
              list="search-history"
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleSearchInputKeyDown}
              placeholder="Search"
              type="search"
              value={input}
            />
            <datalist id="search-history">
              {state.searchHistory.map((q, i) => (
                <option key={i} value={q} />
              ))}
            </datalist>
          </>
        ) : null}
        {isAnalysisPage || isSpikePage ? (
          <DateRangeInput
            alignPopover="end"
            className={styles["hide-on-mobile"]}
            from={from}
            onChange={handleDateRangeChange}
            to={to}
          />
        ) : null}
        {isAnalysisPage || isDiscoveryPage ? (
          <Select
            className={styles["hide-on-mobile"]}
            onChange={handleFilterChange}
            options={[
              { text: "All sources", value: "" },
              { text: "Admin reports", value: "INTERNAL" },
              { text: "Beta program", value: "EXTERNAL" },
              { text: "CS reports", value: "NON_STR_EXTERNAL" },
            ]}
            value={filter ?? ""}
          />
        ) : null}
        {isSpikePage ? (
          <Select
            className={styles["hide-on-mobile"]}
            onChange={handleFilterChange}
            options={[
              { text: "All feedback", value: "ALL_SPIKES" },
              { text: "All dogfooding", value: "ALL_STR_SPIKES" },
              { text: "Beta feedback", value: "EXTERNAL_STR_SPIKES" },
              {
                text: "CS reports",
                value: "EXTERNAL_NON_STR_SPIKES",
              },
              { text: "Admin reports", value: "INTERNAL_STR_SPIKES" },
            ]}
            value={filter ?? "ALL_SPIKES"}
          />
        ) : null}
      </div>
      <div className={styles["loading-dots"]}>
        <LoadingDots type="button" />
      </div>
    </div>
  );
};

export default Topbar;
