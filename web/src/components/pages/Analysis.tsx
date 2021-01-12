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
  "/crash(es|ing|ed)/ OR /freez(e|es|ing)/ OR frozen OR /stop(s|ping|ped)/ unresponsive OR unusable OR slow",
  'I (hate OR "don\'t like")',
  '/refund(ed)?/ OR "money back"',
  "/unlock(ed)?/",
  "fix",
  'how ("do I" OR "can I" OR to)',
  '(latest (update OR version)) OR "last update"',
  "(please (include OR add)) OR /lack(ing|s)/ OR limited",
  "/(chat)?bot(s)?/ OR tutor",
  "pearson OR /class(room|rooms)?/ OR /(student|teacher|assignment|homework|school)(s)?/",
  "/(disappoint|annoy|frustrat|irritat)(ed|ing)/ OR terrible OR horrible OR worst OR bad OR unfortunately OR ridiculous OR /sad(ly)?/",
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
          <span>
            You can use AND/OR with parentheses to specify queries with multiple
            words:
          </span>
          <ul>
            <li>
              <SearchExample query="inappropriate OR offensive" />
            </li>
            <li>
              <SearchExample query="stuck OR (I AND (can't OR couldn't))" />
            </li>
          </ul>
          <span>Use + and - to force a word to be included or excluded:</span>
          <ul>
            <li>
              <SearchExample query="+please add -Icelandic language" />
            </li>
          </ul>
          <span>
            Forward slashes will let you specify regular expressions, but they
            can only match single words:
          </span>
          <ul>
            <li>
              <SearchExample query="/(freeze|frozen|stopped|unresponsive)/" />
            </li>
            <li>
              <SearchExample query="/[0-9]{3,4}/ AND /day[s]?/ AND streak" />
            </li>
          </ul>
          <span>
            Since Jeeves searches per-word at word level, the following are
            equivalent:
          </span>
          <ul>
            <li>
              <SearchExample query="like need want" />
            </li>
            <li>
              <SearchExample query="like OR need OR want" />
            </li>
            <li>
              <SearchExample query="/(like|need|want)/" />
            </li>
          </ul>
          <span>
            Double quotes will let you search for a specific sequence of words:
          </span>
          <ul>
            <li>
              <SearchExample query='"lost my streak"' />
            </li>
            <li>
              <SearchExample query='"how come"' />
            </li>
          </ul>
          <span>Here are some other search suggestions:</span>
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
