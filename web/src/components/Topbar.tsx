import { endOfDay } from "date-fns";
import * as React from "react";
import { useQuery } from "react-query";
import {
  NavLink,
  useHistory,
  useLocation,
  useParams,
  useRouteMatch,
} from "react-router-dom";
import { Input, LoadingDots, Select, SelectList } from "web-ui";

import { encodeURLSearchParams } from "../util";
import { getSpikeCategories } from "api/jeeves";
import cn from "classnames";
import type { DateRangeChangeEvent } from "components/DateRangeInput";
import DateRangeInput from "components/DateRangeInput";
import Hamburger from "components/Hamburger";
import LabelledToggle from "components/LabelledToggle";
import type { SearchInputChangeEvent } from "components/SearchInput";
import SearchInput from "components/SearchInput";
import useDateRangeFilter from "components/useDateRangeFilter";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

type SelectListProps = React.ComponentProps<typeof SelectList>;

type SelectListChangeEvent = Parameters<
  Exclude<SelectListProps["onChange"], undefined>
>[0];

const Topbar = () => {
  const { data: areas = [] } = useFeaturesByTeamAndArea();
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const isAnalysisPage = useRouteMatch("/:lang/analysis");
  const isDiscoveryPage = useRouteMatch("/:lang/discovery");
  const isSpikePage = useRouteMatch("/:lang/spike");
  const isSpikeStatsPage = useRouteMatch("/:lang/spike-stats");
  const search = useSearchParams();

  const area = search.get("area");
  const filter = search.get("filter");
  const query = search.get("q") ?? "";
  const team = search.get("team");
  const useLemmas = search.get("use-lemmas") === "true";

  const { from, to } = useDateRangeFilter({
    daysAgo: isSpikePage ? 3 : undefined,
    monthsAgo: isAnalysisPage || isSpikeStatsPage ? 3 : undefined,
  });

  const [state, dispatch] = React.useContext(AppStateContext);
  const [input, setInput] = React.useState(query);
  const [shouldSubmit, setShouldSubmit] = React.useState(false);
  const [suggestedCaret, setSuggestedCaret] = React.useState<number>();

  const searchInputRef =
    React.useRef<React.ElementRef<typeof SearchInput>>(null);

  const spikeCategories = useQuery("spike-categories", () =>
    getSpikeCategories(),
  );

  const areasAndTeams = React.useMemo(() => {
    const options = areas.flatMap(a => [
      { field: "area", text: a.area_name, value: "" },
      ...a.teams.flatMap(t => ({
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
      area || team
        ? areasAndTeams.findIndex(
            o => (area && o.text === area) || (team && o.text === team),
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
    const val = e.selectedValue
      ? areasAndTeams[parseInt(e.selectedValue, 10)]
      : undefined;
    const params = new URLSearchParams(location.search);
    params.delete("area");
    params.delete("page");
    params.delete("team");
    if (val) {
      params.set(val.field, val.text);
      params.set("filter", "INTERNAL");
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

  const handleUseLemmasChange = () => {
    const params = new URLSearchParams(location.search);
    params.delete("page");
    params.set("use-lemmas", (!useLemmas).toString());
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
  }, [dispatch, query]);

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
                : isSpikeStatsPage
                ? "-spike-stats"
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
        {isAnalysisPage ? (
          <LabelledToggle
            checked={useLemmas}
            className={styles["hide-on-mobile"]}
            onChange={handleUseLemmasChange}
            title="Use lemmas: "
          />
        ) : null}
        {isAnalysisPage || isSpikePage || isSpikeStatsPage ? (
          <DateRangeInput
            alignPopover="end"
            className={styles["hide-on-mobile"]}
            from={from}
            onChange={handleDateRangeChange}
            to={to}
          />
        ) : null}
        {isDiscoveryPage ? (
          <div
            className={cn(styles.area, styles["hide-on-mobile"])}
            onKeyDown={
              // Don't trigger shortcuts.
              e => e.stopPropagation()
            }
          >
            <SelectList
              onChange={handleAreaOrTeamChange}
              options={[{ text: "Any area/team", value: "" }, ...areasAndTeams]}
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
              showSearch={true}
              value={areaOrTeamIndex > -1 ? `${areaOrTeamIndex}` : ""}
            />
          </div>
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
        {isSpikePage || isSpikeStatsPage ? (
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
