import { encodeURLSearchParams } from "util";

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
import type { SearchInputChangeEvent } from "components/SearchInput";
import SearchInput from "components/SearchInput";
import useDateRangeFilter from "components/useDateRangeFilter";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

const Topbar = () => {
  const { from, to } = useDateRangeFilter({
    daysAgo: useRouteMatch("/:lang/spike") ? 3 : undefined,
    monthsAgo: useRouteMatch("/:lang/analysis") ? 3 : undefined,
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
  const [shouldSubmit, setShouldSubmit] = React.useState(false);
  const [suggestedCaret, setSuggestedCaret] = React.useState<number>();

  const searchInputRef =
    React.useRef<React.ElementRef<typeof SearchInput>>(null);

  const applyFilters = (params: URLSearchParams) =>
    history.push({
      ...location,
      search: encodeURLSearchParams(params),
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

  const handleSearchInputChange = (e: SearchInputChangeEvent) => {
    setInput(e.value);
    setSuggestedCaret(e.suggestedCaret);
  };

  const handleSearchInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      setShouldSubmit(true);
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
  }, [input, location, shouldSubmit]);

  React.useEffect(() => {
    if (suggestedCaret !== undefined) {
      searchInputRef.current?.setCaret(suggestedCaret);
      setSuggestedCaret(undefined);
    }
  }, [suggestedCaret]);

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
              className={styles["search-mobile"]}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleSearchInputKeyDown}
              placeholder="Search"
              type="search"
              value={input}
            />
            <SearchInput
              className={styles.search}
              onChange={handleSearchInputChange}
              onKeyDown={handleSearchInputKeyDown}
              ref={searchInputRef}
              value={input}
            />
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
