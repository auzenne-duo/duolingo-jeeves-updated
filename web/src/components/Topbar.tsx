import { useQuery } from "@tanstack/react-query";
import { endOfDay } from "date-fns";
import * as React from "react";
import { NavLink, useHistory, useLocation } from "react-router-dom";
import { LoadingDots, Select, SelectList } from "web-ui";
import { TextInput } from "web-ui/juicy";

import { encodeURLSearchParams } from "../util";
import { getSpikeCategories } from "api/jeeves";
import cn from "classnames";
import type { DateRangeChangeEvent } from "components/DateRangeInput";
import DateRangeInput from "components/DateRangeInput";
import Hamburger from "components/Hamburger";
import LabelledToggle from "components/LabelledToggle";
import type { SearchInputChangeEvent } from "components/SearchInput";
import SearchInput from "components/SearchInput";
import styles from "components/Topbar.scss";
import useDateRangeFilter from "components/useDateRangeFilter";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import usePage, { Page } from "components/usePage";
import usePageLanguage from "components/usePageLanguage";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import imageLogo from "images/logo.svg";

type SelectListProps = React.ComponentProps<typeof SelectList>;

type SelectListChangeEvent = Parameters<
  Exclude<SelectListProps["onChange"], undefined>
>[0];

// eslint-disable-next-line complexity
const Topbar = () => {
  const { data: areas = [] } = useFeaturesByTeamAndArea();
  const history = useHistory();
  const language = usePageLanguage();
  const location = useLocation();
  const page = usePage();
  const search = useSearchParams();

  const area = search.get("area");
  const filter = search.get("filter");
  const query = search.get("q") ?? "";
  const team = search.get("team");
  const onlyBugs = (search.get("only-bugs") ?? "true") === "true";
  const useLemmas = search.get("use-lemmas") === "true";

  const { from, to } = useDateRangeFilter({
    daysAgo: page === Page.Spike ? 3 : undefined,
    monthsAgo:
      page === Page.Analysis || page === Page.SpikeStats ? 3 : undefined,
  });

  const [state, dispatch] = React.useContext(AppStateContext);
  const [input, setInput] = React.useState(query);
  const [shouldSubmit, setShouldSubmit] = React.useState(false);
  const [suggestedCaret, setSuggestedCaret] = React.useState<number>();

  const searchInputRef =
    React.useRef<React.ElementRef<typeof SearchInput>>(null);

  const spikeCategories = useQuery(["spike-categories"], () =>
    getSpikeCategories(),
  );

  const areasAndTeams = React.useMemo(() => {
    const options = areas.flatMap(a => [
      { area: a, field: "area", text: a.area_name, value: "" },
      ...a.teams.flatMap(t => ({
        area: a,
        description: `in ${a.area_name}`,
        field: "team",
        text: t.team_name,
        value: "",
      })),
    ]);
    options.forEach((o, i) => (o.value = `${i}`));
    return options;
  }, [areas]);

  const areaOrTeamIndex = React.useMemo(
    () =>
      area
        ? areasAndTeams.findIndex(o =>
            team
              ? o.field === "team" &&
                o.text === team &&
                o.area.area_name === area
              : o.field === "area" && o.text === area,
          )
        : -1,
    [area, areasAndTeams, team],
  );

  const applyFilters = React.useCallback(
    (params: URLSearchParams) =>
      history.push({
        ...location,
        search: encodeURLSearchParams(params),
      }),
    [history, location],
  );

  const handleAreaOrTeamChange = (e: SelectListChangeEvent) => {
    const val = areasAndTeams[e.selectedIndices[0]];
    const params = new URLSearchParams(location.search);
    params.delete("area");
    params.delete("page");
    params.delete("team");
    if (val) {
      if (val.field === "team") {
        // The team is unique within an area, so also set the area parameter.
        params.set("area", val.area.area_name);
      }
      params.set(val.field, val.text);
      if (page === Page.Discovery) {
        params.set("filter", "INTERNAL");
      }
    }
    applyFilters(params);
  };

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

  const handleUseLemmasClick = () => {
    const params = new URLSearchParams(location.search);
    params.delete("page");
    params.set("use-lemmas", (!useLemmas).toString());
    applyFilters(params);
  };

  const handleOnlyBugsClick = () => {
    const params = new URLSearchParams(location.search);
    params.set("only-bugs", (!onlyBugs).toString());
    params.delete("page");
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
    if (query) {
      // Begin tracking the search query
      dispatch?.({
        language,
        page: page ?? "",
        queryType: page ?? "", // This may diverge from 'page' in the future
        searchString: query,
        timestamp: window.performance.now(),
        type: "SEARCH_BEGIN",
      });
    }
  }, [dispatch, language, page, query]);

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

  React.useEffect(() => {
    if (suggestedCaret !== undefined) {
      searchInputRef.current?.setCaret(suggestedCaret);
      setSuggestedCaret(undefined);
    }
  }, [suggestedCaret]);

  return (
    <div className={cn(styles.wrap, { [styles.loading]: state.loading })}>
      <Hamburger isOpen={state.showMenu} onClick={handleHamburgerClick} />
      <NavLink className={styles["logo-link"]} to={`/${language}`}>
        <img alt="Duolingo Jeeves" className={styles.logo} src={imageLogo} />
        {state.loading ? <LoadingDots type="button" /> : null}
      </NavLink>
      <div className={page ? styles[`filters-${page}`] : styles["filters"]}>
        {page &&
        [
          Page.Analysis,
          Page.Discovery,
          Page.GPTSearch,
          Page.SentimentSearch,
        ].includes(page) ? (
          <>
            <TextInput
              className={styles["search-mobile"]}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleSearchInputKeyDown}
              placeholder="Search"
              type="search"
              value={input}
            />
            <SearchInput
              className={styles.search}
              history={
                [Page.GPTSearch, Page.SentimentSearch].includes(page)
                  ? state.searchHistoryGPT
                  : state.searchHistory
              }
              onChange={handleSearchInputChange}
              onKeyDown={handleSearchInputKeyDown}
              ref={searchInputRef}
              supportsTicketQuery={
                ![Page.GPTSearch, Page.SentimentSearch].includes(page)
              }
              value={input}
            />
          </>
        ) : null}
        {page === Page.Analysis ? (
          <LabelledToggle
            checked={useLemmas}
            className={styles["hide-on-mobile"]}
            onClick={handleUseLemmasClick}
            title="Use lemmas: "
          />
        ) : null}
        {page === Page.Spike ? (
          <LabelledToggle
            checked={onlyBugs}
            className={styles["hide-on-mobile"]}
            onClick={handleOnlyBugsClick}
            title="Only bugs: "
          />
        ) : null}
        {page && [Page.Analysis, Page.Spike, Page.SpikeStats].includes(page) ? (
          <DateRangeInput
            alignPopover="end"
            className={styles["hide-on-mobile"]}
            from={from}
            onChange={handleDateRangeChange}
            to={to}
          />
        ) : null}
        {page && [Page.Discovery, Page.QualityReport].includes(page) ? (
          <div
            className={cn(styles.area, styles["hide-on-mobile"])}
            onKeyDown={
              // Don't trigger shortcuts.
              e => e.stopPropagation()
            }
          >
            <SelectList
              items={areasAndTeams}
              onChange={handleAreaOrTeamChange}
              popoverPosition={{
                direction: "down",
                manualPositioning: true,
                style: {
                  maxHeight: "min(50vh, 400px)",
                  maxWidth: "min(50vw, 300px)",
                  position: "absolute",
                  right: 0,
                  top: "100%",
                  width: "max-content",
                },
                zIndex: 1,
              }}
              selectedIndices={areaOrTeamIndex > -1 ? [areaOrTeamIndex] : []}
              showSearch={true}
              text={areaOrTeamIndex > -1 ? undefined : "Any area/team"}
            />
          </div>
        ) : null}
        {page && [Page.Analysis, Page.Discovery].includes(page) ? (
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
        {page && [Page.Spike, Page.SpikeStats].includes(page) ? (
          <Select
            className={styles["hide-on-mobile"]}
            onChange={handleFilterChange}
            options={spikeCategories.data ?? []}
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
