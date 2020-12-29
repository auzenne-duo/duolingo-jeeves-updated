import { debounce } from "lodash";
import * as React from "react";
import { useHistory, useLocation, useParams } from "react-router-dom";
import { Button } from "web-ui";

import { getTickets } from "api";
import Pagination from "components/Pagination";
import SearchExample from "components/SearchExample";
import TicketTable from "components/TicketTable";
import TrendGraph, { RangeChangeEvent } from "components/TrendGraph";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import styles from "styles/pages/Analysis.scss";
import { encodeURLSearchParams, getPaginationString } from "util";

const EXAMPLES = [
  "crash(es|ing|ed)|freez(e|es|ing)|frozen|stop(s|ping|ped)|unresponsive|unusable|slow",
  "lost .+? streak",
  "I (hate|don't like)",
  "refund(ed)?|money back",
  "unlock(ed)?",
  "fix",
  "how (do I|can I|to)",
  "why|how come",
  "latest (update|version)|last update",
  "please (include|add)|lack(ing|s)|limited",
  "inappropriate|offensive",
  "stuck|I (can't|couldn't)",
  "(chat)?bot(s)?|tutor",
  "pearson|class(room|rooms)?|(student|teacher|assignment|homework|school)(s)?",
  "(disappoint|annoy|frustrat|irritat)(ed|ing)|terrible|horrible|worst|bad|unfortunately|ridiculous|sad(ly)?",
];

const PER_PAGE = 10;

const handleRangeChangeDebouncer = debounce(
  (callback: Function) => callback(),
  500,
);

const Analysis = () => {
  const { from, to } = useDateRangeFilter();
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
    page: string | undefined;
  }>();
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);
  const [showTrend, setShowTrend] = React.useState(true);

  const page = search.get("page")
    ? parseInt(search.get("page") as string, 10)
    : 1;
  const query = search.get("q") ?? "";

  const nextQuery = useSearchParams();
  nextQuery.set("page", `${page + 1}`);

  const prevQuery = useSearchParams();
  prevQuery.set("page", `${page - 1}`);

  const [
    { data: tickets, next_url: nextUrl, total_records: totalTickets },
    isLoading,
  ] = useAwaitedValue(
    { data: undefined, next_url: undefined, total_records: undefined },
    async () =>
      query
        ? await getTickets(lang, {
            end_time: to,
            limit: PER_PAGE,
            page: page - 1,
            start_time: from,
            word: query,
          })
        : { data: undefined, next_url: undefined, total_records: undefined },
    [from?.valueOf(), lang, page, query, to?.valueOf()],
  );

  const handleRangeChange = (e: RangeChangeEvent) => {
    if (e.from) {
      search.set("from", e.from.toJSON());
    } else {
      search.delete("from");
    }
    if (e.to) {
      search.set("to", e.to.toJSON());
    } else {
      search.delete("to");
    }
    if (e.from || e.to) {
      search.delete("page");
      ga("send", "event", {
        eventCategory: "Tickets",
        eventAction: "modify_range",
      });
    }
    history.push({
      ...location,
      search: encodeURLSearchParams(search),
    });
  };

  useDocumentTitle("Time Series Analyzer");
  usePageView();

  React.useEffect(() => {
    if (isLoading) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
  }, [isLoading]);

  React.useEffect(() => {
    if (page > 1) {
      setShowTrend(false);
    }
  }, [page]);

  React.useEffect(() => {
    setShowTrend(true);
  }, [query]);

  React.useEffect(() => {
    ga("send", "event", {
      eventCategory: "Tickets",
      eventAction: "search",
      eventLabel: query,
    });
  }, [query]);

  const paginationString = isLoading
    ? undefined
    : getPaginationString({
        page,
        perPage: PER_PAGE,
        total: totalTickets,
      });

  return (
    <>
      {query ? (
        <>
          <div className={styles["trend-header"]}>
            <h2>Trend</h2>
            <Button
              onClick={() => setShowTrend(value => !value)}
              variant="stroke"
            >
              {showTrend ? "Hide" : "Show"}
            </Button>
          </div>
          <div className={styles[`trend${showTrend ? "" : "-hidden"}`]}>
            <TrendGraph
              language={lang}
              onRangeChange={e =>
                handleRangeChangeDebouncer(() => handleRangeChange(e))
              }
              query={query}
              zoomFrom={from}
              zoomTo={to}
            />
          </div>
          <h2 className={showTrend ? "" : styles["tickets-after-hidden-trend"]}>
            {paginationString
              ? `Showing ${paginationString} tickets`
              : "Tickets"}
          </h2>
          {isLoading ? null : tickets?.length ? (
            tickets.map((t, i) => (
              <TicketTable highlight={query} key={i} ticket={t} />
            ))
          ) : (
            <span>Your search returned no results.</span>
          )}
        </>
      ) : (
        <div className={styles.explanation}>
          <span>You can use regular expressions, for example:</span>
          <ul>
            <li>
              <SearchExample query="(freeze|frozen|stopped|unresponsive)" />
            </li>
            <li>
              <SearchExample query="[0-9]{(3, 4)}.day[s]? streak" />
            </li>
            <li>
              <SearchExample query="lost.+?streak" />
            </li>
          </ul>
          <span>Or try one of these suggestions:</span>
          <ul>
            {EXAMPLES.map((q, i) => (
              <li key={i}>
                <SearchExample query={q} />
              </li>
            ))}
          </ul>
        </div>
      )}
      {nextUrl || page > 1 ? (
        <Pagination
          nextLink={
            nextUrl
              ? {
                  ...location,
                  search: encodeURLSearchParams(nextQuery),
                }
              : undefined
          }
          prevLink={
            page > 1
              ? {
                  ...location,
                  search: encodeURLSearchParams(prevQuery),
                }
              : undefined
          }
        />
      ) : null}
    </>
  );
};

export default Analysis;
