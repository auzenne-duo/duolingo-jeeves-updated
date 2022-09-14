import {
  encodeURLSearchParams,
  formatCourseId,
  formatReadableDate,
  formatScreen,
  getFilterLink,
  getPaginationString,
  getUntruncatedTitle,
} from "util";

import { format, formatISO, isThisYear, isToday } from "date-fns";
import { debounce } from "lodash";
import * as React from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "react-query";
import { Link, useHistory, useLocation, useParams } from "react-router-dom";
import { alignNearest } from "web-ui/util/scroll";

import { getTicket, getTickets } from "api/jeeves";
import JiraStatus from "components/JiraStatus";
import Pagination from "components/Pagination";
import PlatformIcon from "components/PlatformIcon";
import Tag from "components/Tag";
import TagFilter from "components/TagFilter";
import Ticket from "components/Ticket";
import type { RangeChangeEvent } from "components/TrendGraph";
import TrendGraph from "components/TrendGraph";
import useDateRangeFilter from "components/useDateRangeFilter";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import styles from "styles/Tickets.scss";

const PER_PAGE = 30;

const formatDate = (date: Date) => {
  if (isToday(date)) {
    return format(date, "HH:mm");
  }
  if (isThisYear(date)) {
    return format(date, "d MMM");
  }
  return formatISO(date, { representation: "date" });
};

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
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
  }>();
  const queryClient = useQueryClient();
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);
  const currentRowRef = React.useRef<HTMLLIElement>(null);

  const area = search.get("area");
  const filter = search.get("filter") as JSONAPI.ShakeToReportCategory | null;
  const id = search.get("id");
  const offset = search.get("offset")
    ? parseInt(search.get("offset") as string, 10)
    : 0;
  const prevSortId = search.get("prev-sort-id");
  const sortId = search.get("sort-id");
  const spikeCategory = (search.get("spike-category") ??
    "ALL_SPIKES") as JSONAPI.SpikeCategory;
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

  const nextQuery = useSearchParams();
  nextQuery.set("offset", `${offset + PER_PAGE}`);
  nextQuery.set("sort-id", `${data?.next_sort_id}`);
  nextQuery.delete("prev-sort-id");
  const nextLink =
    data?.next_sort_id && !isPreviousData
      ? {
          ...location,
          search: encodeURLSearchParams(nextQuery),
        }
      : undefined;

  const prevQuery = useSearchParams();
  prevQuery.set("offset", `${offset - PER_PAGE}`);
  prevQuery.set("prev-sort-id", `${data?.prev_sort_id}`);
  prevQuery.delete("sort-id");
  const prevLink =
    offset > 0
      ? {
          ...location,
          search: encodeURLSearchParams(prevQuery),
        }
      : undefined;

  const { data: selected } = useQuery(
    ["tickets", id, { lang }],
    () => getTicket(lang, id as string),
    {
      enabled: !!id,
      initialData: () =>
        queryClient
          .getQueryData<JSONAPI.Tickets>(listQueryKey)
          ?.data.find(t => t.jeeves_uid === id),
      initialDataUpdatedAt: () =>
        queryClient.getQueryState(listQueryKey)?.dataUpdatedAt,
    },
  );

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
      ga("send", "event", {
        eventAction: "modify_range",
        eventCategory: "Tickets",
      });
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

  const setId = (newId: string | undefined) => {
    const params = new URLSearchParams(location.search);
    if (newId === undefined) {
      params.delete("id");
    } else {
      params.set("id", newId);
    }
    history.push({
      ...location,
      search: encodeURLSearchParams(params),
    });
  };

  React.useEffect(() => {
    dispatch?.({ type: "HIDE_ASIDE" });
  }, [filter, query]);

  React.useEffect(() => {
    if (id) {
      dispatch?.({ type: "SHOW_ASIDE" });
      return () => {
        dispatch?.({ type: "HIDE_ASIDE" });
      };
    }
    return undefined;
  }, [id]);

  React.useEffect(() => {
    if (id) {
      const handleKeydown = (e: KeyboardEvent) => {
        if (e.key === "]") {
          dispatch?.({ type: "TOGGLE_ASIDE" });
          e.preventDefault();
        }
      };
      document.addEventListener("keydown", handleKeydown);
      return () => document.removeEventListener("keydown", handleKeydown);
    }
    return undefined;
  }, [id]);

  React.useEffect(() => {
    if (currentRowRef.current) {
      const bodyStyle = getComputedStyle(document.body);
      const topbarHeight = parseFloat(
        bodyStyle.getPropertyValue("--height-topbar"),
      );
      const margin = parseFloat(bodyStyle.getPropertyValue("--margin"));
      const target = currentRowRef.current.getBoundingClientRect();
      document.documentElement.scrollTop += alignNearest(
        topbarHeight + margin,
        window.innerHeight - margin,
        window.innerHeight - topbarHeight - 2 * margin,
        0,
        0,
        target.top,
        target.bottom,
        target.height,
      );
    }
  }, [id, tickets]);

  React.useEffect(() => {
    if (tickets?.length) {
      const currentIndex = tickets.findIndex(t => t.jeeves_uid === id);

      const next = () => {
        if (currentIndex < tickets.length - 1) {
          setId(tickets[currentIndex + 1].jeeves_uid);
        } else if (nextLink) {
          history.push(nextLink);
        }
      };

      const prev = () => {
        if (currentIndex === -1) {
          setId(tickets[tickets.length - 1].jeeves_uid);
        } else if (currentIndex > 0) {
          setId(tickets[currentIndex - 1].jeeves_uid);
        } else if (prevLink) {
          history.push(prevLink);
        }
      };

      const handleKeydown = (e: KeyboardEvent) => {
        if (e.key === "j") {
          next();
          e.preventDefault();
        } else if (e.key === "k") {
          prev();
          e.preventDefault();
        }
      };
      document.addEventListener("keydown", handleKeydown);
      return () => document.removeEventListener("keydown", handleKeydown);
    }
    return undefined;
  }, [id, nextLink, prevLink, setId, tickets]);

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
          <ul className={styles.list}>
            {tickets?.map((t, i) => {
              const date = t.date_time ? new Date(t.date_time) : undefined;
              return (
                <li
                  className={
                    styles[
                      `item${
                        t.jeeves_uid === selected?.jeeves_uid ? "-selected" : ""
                      }`
                    ]
                  }
                  key={i}
                  onClick={() => handleClick(t)}
                  ref={
                    t.jeeves_uid === selected?.jeeves_uid
                      ? currentRowRef
                      : undefined
                  }
                >
                  <div className={styles["title-container"]}>
                    <span className={styles.title}>
                      {getUntruncatedTitle(t)}
                    </span>
                  </div>
                  <div className={styles.tags}>
                    {t.issue_key ? (
                      <Tag className={styles["tag-ipad"]} value={t.issue_key} />
                    ) : null}
                    {t.course ? (
                      <TagFilter
                        className={styles["tag-ipad"]}
                        field="course"
                        text={formatCourseId(t.course)}
                        value={t.course}
                      />
                    ) : null}
                    {t.screen_content ? (
                      <TagFilter
                        className={styles["tag-ipad"]}
                        field="screen_content"
                        text={formatScreen(t.screen_content)}
                        value={t.screen_content}
                      />
                    ) : null}
                    {t.app_version ? (
                      <TagFilter
                        className={styles["tag-ipad"]}
                        field="app_version"
                        text={
                          t.platform === "Web"
                            ? t.app_version.slice(0, 7)
                            : t.app_version
                        }
                        value={t.app_version}
                      />
                    ) : null}
                    {t.data_source === "JIRA" && t.status ? (
                      <Link
                        className={styles["tag-jira"]}
                        onClick={e => e.stopPropagation()}
                        to={getFilterLink(location, "status", t.status)}
                      >
                        <JiraStatus status={t.status} />
                      </Link>
                    ) : null}
                    {t.platform ? (
                      <Link
                        className={styles["tag-platform"]}
                        onClick={e => e.stopPropagation()}
                        to={getFilterLink(location, "platform", t.platform)}
                      >
                        <PlatformIcon
                          className={styles.icon}
                          platform={t.platform}
                        />
                      </Link>
                    ) : t.data_source === "Zendesk" &&
                      t.via?.channel === "twitter" ? (
                      <Link
                        className={styles["tag-platform"]}
                        onClick={e => e.stopPropagation()}
                        to={getFilterLink(location, "via.channel", "twitter")}
                      >
                        <PlatformIcon
                          className={styles.icon}
                          platform="Twitter"
                        />
                      </Link>
                    ) : null}
                    {date ? (
                      <span
                        className={styles.date}
                        title={formatReadableDate(date)}
                      >
                        {formatDate(date)}
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
          <div className={styles.pagination}>
            {getPaginationString({
              offset,
              perPage: PER_PAGE,
              total: data?.total_records,
            })}
          </div>
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
              highlight={query}
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
