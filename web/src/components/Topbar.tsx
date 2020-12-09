import { endOfDay } from "date-fns";
import * as React from "react";
import {
  NavLink,
  Route,
  useHistory,
  useLocation,
  useParams,
  useRouteMatch,
} from "react-router-dom";
import { Input, LoadingDots, Select } from "web-ui";

import DateRangeInput, {
  DateRangeChangeEvent,
} from "components/DateRangeInput";
import useDateRangeFilter from "components/useDateRangeFilter";
import useSearchParams from "components/useSearchParams";
import imageLogo from "images/logo.svg";
import styles from "styles/Topbar.scss";

interface Props {
  isLoading: boolean;
}

const Topbar: React.FC<Props> = ({ isLoading }) => {
  const { from, to } = useDateRangeFilter({
    daysAgo: useRouteMatch("/:lang/spike") ? 3 : 0,
  });
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const showSearchInput = useRouteMatch("/:lang/(analysis|discovery)");
  const search = useSearchParams();

  const filter = search.get("filter");
  const query = search.get("q") ?? "";

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
    }
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
        <Route path="/:lang/(analysis|discovery|spike)">
          <div className={styles[`filters${showSearchInput ? "-search" : ""}`]}>
            {showSearchInput ? (
              <Input
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleSearchInputKeyDown}
                placeholder="Search"
                type="search"
                value={input}
              />
            ) : null}
            <Route path="/:lang/(analysis|spike)">
              <DateRangeInput
                alignPopover="end"
                from={from}
                onChange={handleDateRangeChange}
                to={to}
              />
            </Route>
            <Route path="/:lang/discovery">
              <Select
                onChange={handleFilterChange}
                options={[
                  { text: "All sources", value: "" },
                  { text: "Admin reports", value: "INTERNAL" },
                  { text: "Beta program", value: "EXTERNAL" },
                  { text: "CS reports", value: "NON_STR_EXTERNAL" },
                ]}
                value={filter ?? ""}
              />
            </Route>
            <Route path="/:lang/spike">
              <Select
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
          </div>
        </Route>
      </nav>
    </div>
  );
};

export default Topbar;
