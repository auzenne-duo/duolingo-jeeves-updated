import { format, formatISO, isThisYear, isToday } from "date-fns";
import * as React from "react";
import { createPortal } from "react-dom";
import { useHistory, useLocation, useParams } from "react-router-dom";

import { getTicket, getTickets } from "api";
import Pagination from "components/Pagination";
import PlatformIcon from "components/PlatformIcon";
import Tag from "components/Tag";
import Ticket from "components/Ticket";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import styles from "styles/pages/Discovery.scss";
import {
  encodeURLSearchParams,
  formatCourseId,
  formatReadableDate,
  formatScreen,
  getPaginationString,
} from "util";

const PER_PAGE = 50;

const formatDate = (date: Date) => {
  if (isToday(date)) {
    return format(date, "HH:mm");
  }
  if (isThisYear(date)) {
    return format(date, "d MMM");
  }
  return formatISO(date, { representation: "date" });
};

const Discovery = () => {
  const history = useHistory();
  const location = useLocation();
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
    page: string | undefined;
  }>();
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);
  const lastSelectedRef = React.useRef<JSONAPI.Ticket>();

  const filter = search.get("filter") as JSONAPI.ShakeToReportCategory | null;
  const id = search.get("id");
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
    () =>
      getTickets(lang, {
        beta_filter: filter ?? undefined,
        limit: PER_PAGE,
        page: page - 1,
        word: query,
      }),
    [filter, lang, page, query],
  );

  const [selected, isLoadingSelected] = useAwaitedValue(
    undefined,
    async () => {
      // If we've already fetched the ticket, return the
      // previous result to avoid extra API calls.
      if (id === lastSelectedRef.current?.jeeves_uid) {
        return lastSelectedRef.current;
      } else if (id) {
        return (
          // If the ticket exists on the current page, return
          // the existing result to avoid extra API calls.
          tickets?.find(t => t.jeeves_uid === id) || (await getTicket(lang, id))
        );
      }
      return undefined;
    },
    [id, lang, tickets],
  );

  const handleClick = (t: JSONAPI.Ticket) => {
    if (t.jeeves_uid === selected?.jeeves_uid) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid);
    }
  };

  const setId = (id: string | undefined) => {
    const params = new URLSearchParams(location.search);
    if (id === undefined) {
      params.delete("id");
    } else {
      params.set("id", id);
    }
    history.push({
      ...location,
      search: params.toString(),
    });
  };

  useDocumentTitle("Issue Discovery");
  usePageView();

  React.useEffect(() => {
    lastSelectedRef.current = selected;
  });

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
  }, [id]);

  React.useEffect(() => {
    if (tickets?.length) {
      const next = () =>
        setId(
          tickets[
            Math.min(
              tickets.findIndex(t => t.jeeves_uid === id) + 1,
              tickets.length - 1,
            )
          ].jeeves_uid,
        );

      const prev = () => {
        const currentIndex = tickets.findIndex(t => t.jeeves_uid === id);
        setId(
          tickets[
            Math.max(
              currentIndex > -1 ? currentIndex - 1 : tickets.length - 1,
              0,
            )
          ].jeeves_uid,
        );
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
  }, [id, setId, tickets]);

  React.useEffect(() => {
    if (!isLoading) {
      window.scrollTo(0, 0);
    }
  }, [isLoading]);

  React.useEffect(() => {
    if (isLoading || isLoadingSelected) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
  }, [isLoading, isLoadingSelected]);

  return (
    <>
      {tickets?.length ? (
        <>
          <ul className={styles.list}>
            {tickets?.map((t, i) => {
              const summary =
                !t.header_text ||
                // Header text for tickets reported via the Zendesk mobile SDK
                // is often truncated after just a few characters.
                (t.data_source === "Zendesk" && t.via?.channel === "mobile_sdk")
                  ? t.body_text?.trim().split(/\n|\.\s/)[0]
                  : t.header_text;
              const date =
                t.data_source === "JIRA" && t.creation_date
                  ? new Date(t.creation_date)
                  : t.date_time
                  ? new Date(t.date_time)
                  : undefined;
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
                >
                  <span className={styles.title}>{summary}</span>
                  <div className={styles.tags}>
                    {t.issue_key ? <Tag value={t.issue_key} /> : null}
                    {t.course ? (
                      <Tag text={formatCourseId(t.course)} value={t.course} />
                    ) : null}
                    {t.screen_content ? (
                      <Tag
                        text={formatScreen(t.screen_content)}
                        value={t.screen_content}
                      />
                    ) : null}
                    {t.app_version ? (
                      <Tag
                        text={
                          t.platform === "Web"
                            ? t.app_version.slice(0, 7)
                            : t.app_version
                        }
                        value={t.app_version}
                      />
                    ) : null}
                    {t.platform ? (
                      <PlatformIcon
                        className={styles.icon}
                        platform={t.platform}
                      />
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
              page,
              perPage: PER_PAGE,
              total: totalTickets,
            })}
          </div>
        </>
      ) : isLoading ? null : (
        <span>Your search returned no results.</span>
      )}
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
      {selected
        ? createPortal(
            <Ticket
              className={styles.ticket}
              onRequestClose={() => setId(undefined)}
              ticket={selected}
            />,
            document.getElementById("aside") as HTMLElement,
          )
        : null}
    </>
  );
};

export default Discovery;
