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
import * as React from "react";
import { createPortal } from "react-dom";
import { useQuery, useQueryClient } from "react-query";
import { Link, useHistory, useLocation, useParams } from "react-router-dom";

import { getTicket, getTickets } from "api";
import JiraStatus from "components/JiraStatus";
import Pagination from "components/Pagination";
import PlatformIcon from "components/PlatformIcon";
import Tag from "components/Tag";
import TagFilter from "components/TagFilter";
import Ticket from "components/Ticket";
import useDocumentTitle from "components/useDocumentTitle";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";
import styles from "styles/pages/Discovery.scss";

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

const Discovery = () => {
  const history = useHistory();
  const { data: areas = [], isSuccess: areasLoaded } =
    useFeaturesByTeamAndArea();
  const location = useLocation();
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
    page: string | undefined;
  }>();
  const queryClient = useQueryClient();
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);

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

  const listQueryKey = ["tickets", { areas, filter, lang, page, query }];

  const { data, error, isLoading, isPreviousData } = useQuery(
    listQueryKey,
    () =>
      getTickets(lang, {
        areas,
        beta_filter: filter ?? undefined,
        limit: PER_PAGE,
        page: page - 1,
        word: query,
      }),
    { enabled: areasLoaded, keepPreviousData: true },
  );

  const tickets = data?.data;

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

  const setId = (newId: string | undefined) => {
    const params = new URLSearchParams(location.search);
    if (newId === undefined) {
      params.delete("id");
    } else {
      params.set("id", newId);
    }
    history.push({
      ...location,
      search: params.toString(),
    });
  };

  useDocumentTitle("Issue Discovery");
  usePageView();

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
    return undefined;
  }, [id, setId, tickets]);

  React.useEffect(() => {
    if (!isPreviousData) {
      window.scrollTo(0, 0);
    }
  }, [isPreviousData]);

  return (
    <>
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
              total: data?.total_records,
            })}
          </div>
        </>
      ) : error ? (
        <span>Failed to retrieve data.</span>
      ) : isLoading ? null : (
        <span>Your search returned no results.</span>
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
