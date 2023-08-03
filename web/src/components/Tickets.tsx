import { useQuery, useQueryClient } from "@tanstack/react-query";
import { debounce } from "lodash";
import * as React from "react";
import { createPortal } from "react-dom";
import { useHistory, useLocation } from "react-router-dom";
import { Button } from "web-ui";
import { escapeRegExp } from "web-ui/util";
import { getIndices } from "web-ui/util/highlight";

import {
  downloadAsCsv,
  encodeURLSearchParams,
  getPaginationString,
} from "../util";
import { getTickets } from "api/jeeves";
import Pagination from "components/Pagination";
import Ticket from "components/Ticket";
import TicketList from "components/TicketList";
import styles from "components/Tickets.scss";
import type { RangeChangeEvent } from "components/TrendGraph";
import TrendGraph from "components/TrendGraph";
import useDateRangeFilter from "components/useDateRangeFilter";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import usePageLanguage from "components/usePageLanguage";
import useSearchParams from "components/useSearchParams";
import useTicketAside from "components/useTicketAside";
import useTicketQuery from "components/useTicketQuery";
import useTicketSelection from "components/useTicketSelection";
import AppStateContext from "contexts/AppStateContext";

const PER_PAGE = 30;

const handleRangeChangeDebouncer = debounce(
  (callback: () => void) => callback(),
  500,
);

interface Props {
  hasTrend?: boolean;
  monthsAgo?: number;
}

const Tickets = ({ hasTrend, monthsAgo }: Props) => {
  const { from, to } = useDateRangeFilter({ monthsAgo });
  const { data: areas = [], isSuccess: areasLoaded } =
    useFeaturesByTeamAndArea();
  const history = useHistory();
  const location = useLocation();
  const lang = usePageLanguage();
  const queryClient = useQueryClient();
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);

  const area = search.get("area");
  const filter = search.get("filter") as JSONAPI.ShakeToReportCategory | null;
  const offset = search.get("offset")
    ? parseInt(search.get("offset") as string, 10)
    : 0;
  const prevSortId = search.get("prev-sort-id");
  const sortId = search.get("sort-id");
  const spikeCategory = search.get("spike-category") ?? "ALL_SPIKES";
  const team = search.get("team");
  const useLemmas = search.get("use-lemmas") === "true";

  const query = [
    search.get("q") ?? "",
    area ? `area:"${area}"` : "",
    team ? `team:"${team}"` : "",
  ]
    .filter(term => term)
    .map((term, _i, list) => (list.length > 1 ? `(${term})` : term))
    .join(" AND ");

  const listQueryKey = [
    "tickets",
    {
      areas,
      filter,
      from,
      lang,
      offset,
      prevSortId,
      query,
      sortId,
      spikeCategory,
      to,
    },
  ];

  const { data, error, isLoading, isPreviousData } = useQuery(
    listQueryKey,
    () =>
      getTickets(lang, {
        areas,
        beta_filter: filter ?? undefined,
        end_time: to,
        limit: PER_PAGE,
        offset,
        prev_sort_id: prevSortId ?? undefined,
        sort_id: sortId ?? undefined,
        spike_category: spikeCategory,
        start_time: from,
        use_lemmas: useLemmas,
        word: query,
      }),
    { enabled: areasLoaded, keepPreviousData: true },
  );

  const tickets = data?.data;
  const numResults = data?.total_records ?? 0;

  React.useEffect(() => {
    if (data) {
      dispatch?.({
        numResults,
        timestamp: window.performance.now(),
        type: "SEARCH_END",
      });
    }
  }, [data, dispatch, numResults]);

  const [id, setId] = useTicketSelection(tickets, {
    onNext: () => nextLink && history.push(nextLink),
    onPrev: () => prevLink && history.push(prevLink),
  });
  useTicketAside(id);

  const nextQuery = useSearchParams();
  nextQuery.set("offset", `${offset + PER_PAGE}`);
  nextQuery.set("sort-id", `${data?.next_sort_id}`);
  nextQuery.delete("prev-sort-id");
  const nextLink = React.useMemo(
    () =>
      data?.next_sort_id && !isPreviousData
        ? {
            ...location,
            search: encodeURLSearchParams(nextQuery),
          }
        : undefined,
    [data?.next_sort_id, isPreviousData, location, nextQuery],
  );

  const prevQuery = useSearchParams();
  prevQuery.set("offset", `${offset - PER_PAGE}`);
  prevQuery.set("prev-sort-id", `${data?.prev_sort_id}`);
  prevQuery.delete("sort-id");
  const prevLink = React.useMemo(
    () =>
      offset > 0
        ? {
            ...location,
            search: encodeURLSearchParams(prevQuery),
          }
        : undefined,
    [location, offset, prevQuery],
  );

  const { data: selected } = useTicketQuery(id, {
    initialData: () =>
      queryClient
        .getQueryData<JSONAPI.Tickets>(listQueryKey)
        ?.data.find(t => t.jeeves_uid === id),
    initialDataUpdatedAt: () =>
      queryClient.getQueryState(listQueryKey)?.dataUpdatedAt,
  });

  const handleClick = (t: JSONAPI.Ticket) => {
    if (t.jeeves_uid === selected?.jeeves_uid) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid);
    }
  };

  const handleRangeChange = (e: RangeChangeEvent) => {
    const params = new URLSearchParams(location.search);
    if (e.from) {
      params.set("from", e.from.toJSON());
    } else {
      params.delete("from");
    }
    if (e.to) {
      params.set("to", e.to.toJSON());
    } else {
      params.delete("to");
    }
    if (e.from || e.to) {
      params.delete("page");
    }
    history.push({
      ...location,
      search: encodeURLSearchParams(params),
    });
  };

  // Store the callback in a ref to ensure the latest
  // props and state are captured when it's debounced.
  const handleRangeChangeRef = React.useRef(handleRangeChange);
  handleRangeChangeRef.current = handleRangeChange;

  React.useEffect(() => {
    dispatch?.({ type: "HIDE_ASIDE" });
  }, [dispatch, filter, query]);

  // This has a dependency on both `isPreviousData` and `offset` so
  // that the page is scrolled to the top when either cached or
  // fresh query data is loaded.
  React.useEffect(() => {
    if (!isPreviousData) {
      window.scrollTo(0, 0);
    }
  }, [isPreviousData, offset]);

  return (
    <>
      {hasTrend ? (
        <div className={styles.trend}>
          <TrendGraph
            filter={filter ?? undefined}
            language={lang}
            onRangeChange={e =>
              handleRangeChangeDebouncer(() => handleRangeChangeRef.current(e))
            }
            query={query}
            spikeCategory={spikeCategory}
            useLemmas={useLemmas}
            zoomFrom={from}
            zoomTo={to}
          />
        </div>
      ) : null}
      {tickets?.length ? (
        <>
          <TicketList
            onClick={handleClick}
            selectedId={id}
            supportsTicketQuery={true}
            tickets={tickets}
          />
          <div className={styles.pagination}>
            {getPaginationString({
              offset,
              perPage: PER_PAGE,
              total: data?.total_records,
            })}
          </div>
          <Button onClick={() => downloadAsCsv(tickets)} variant="stroke">
            Download data
          </Button>
        </>
      ) : error ? (
        <span>Failed to retrieve data.</span>
      ) : isLoading ? null : (
        <span>Your search returned no results.</span>
      )}
      {nextLink || prevLink ? (
        <Pagination nextLink={nextLink} prevLink={prevLink} />
      ) : null}
      {selected
        ? createPortal(
            <Ticket
              className={styles.ticket}
              highlight={getIndices(
                selected.body_text ?? "",
                new RegExp(escapeRegExp(query), "i"),
              )}
              // Don't reuse the component for different tickets as it's stateful.
              key={selected.jeeves_uid}
              onRequestClose={() => setId(undefined)}
              ticket={selected}
            />,
            document.getElementById("aside") as HTMLElement,
          )
        : null}
    </>
  );
};

export default Tickets;
