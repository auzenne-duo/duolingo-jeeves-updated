import { encodeURLSearchParams, getPaginationString } from "util";

import { debounce } from "lodash";
import * as React from "react";
import { useQuery } from "react-query";
import { useHistory, useLocation, useParams } from "react-router-dom";
import { Button } from "web-ui";

import { getTickets } from "api";
import Pagination from "components/Pagination";
import SearchExample from "components/SearchExample";
import TicketTable from "components/TicketTable";
import type { RangeChangeEvent } from "components/TrendGraph";
import TrendGraph from "components/TrendGraph";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import styles from "styles/pages/Analysis.scss";

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
  (callback: () => void) => callback(),
  500,
);

const Analysis = () => {
  const { from, to } = useDateRangeFilter({ monthsAgo: 3 });
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
    page: string | undefined;
  }>();
  const search = useSearchParams();

  const [showTrend, setShowTrend] = React.useState(true);

  const filter = search.get("filter") as JSONAPI.ShakeToReportCategory | null;
  const page = search.get("page")
    ? parseInt(search.get("page") as string, 10)
    : 1;
  const query = search.get("q") ?? "";

  const nextQuery = useSearchParams();
  nextQuery.set("page", `${page + 1}`);

  const prevQuery = useSearchParams();
  prevQuery.set("page", `${page - 1}`);

  const { data, error, isLoading, isPreviousData } = useQuery(
    ["tickets", { filter, from, lang, page, query, to }],
    () =>
      getTickets(lang, {
        beta_filter: filter ?? undefined,
        end_time: to,
        limit: PER_PAGE,
        page: page - 1,
        start_time: from,
        word: query,
      }),
    {
      enabled: !!query,
      keepPreviousData: true,
    },
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
        eventAction: "modify_range",
        eventCategory: "Tickets",
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
    if (!isPreviousData) {
      window.scrollTo(0, 0);
    }
  }, [isPreviousData]);

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
      eventAction: "search",
      eventCategory: "Tickets",
      eventLabel: query,
    });
  }, [query]);

  const paginationString = isLoading
    ? undefined
    : getPaginationString({
        page,
        perPage: PER_PAGE,
        total: data?.total_records,
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
          {data?.data?.length ? (
            data.data.map((t, i) => (
              <TicketTable highlight={query} key={i} ticket={t} />
            ))
          ) : error ? (
            <span>Failed to retrieve data.</span>
          ) : isLoading ? null : (
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
          <span>
            You can specify a field to search by, if you have the full name of
            the field. For example, these queries will find tickets for
            particular app versions on iOS and Web, respectively, and tickets
            from Luis707110 on iOS:
            <ul>
              <li>
                <SearchExample query='app_version:"6.100.0.3"' />
              </li>
              <li>
                <SearchExample query='app_version:"1d5ab12bdfe724c626843f3db7b29bcb0e52618a"' />
              </li>
              <li>
                <SearchExample query='username:"Luis707110" AND platform:"iOS"' />
              </li>
            </ul>
          </span>

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
      {(data?.next_url && !isPreviousData) || page > 1 ? (
        <Pagination
          nextLink={
            data?.next_url && !isPreviousData
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
