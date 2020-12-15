import { format, formatISO, isThisYear, isToday } from "date-fns";
import * as React from "react";
import { createPortal } from "react-dom";
import { useLocation, useParams } from "react-router-dom";

import { getTickets } from "api";
import { AppDispatch } from "components/App";
import Pagination from "components/Pagination";
import Tag from "components/Tag";
import Ticket from "components/Ticket";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import imagePlatformAndroid from "images/android.svg";
import imagePlatformApple from "images/apple.svg";
import imagePlatformWeb from "images/web.svg";
import styles from "styles/pages/Discovery.scss";
import {
  encodeURLSearchParams,
  formatCourseId,
  formatReadableDate,
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
  const location = useLocation();
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
    page: string | undefined;
  }>();
  const search = useSearchParams();

  const dispatch = React.useContext(AppDispatch);
  const [selected, setSelected] = React.useState<JSONAPI.Ticket>();

  const filter = search.get("filter");
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
        beta_filter: filter as JSONAPI.ShakeToReportCategory,
        limit: PER_PAGE,
        page: page - 1,
        word: query,
      }),
    [filter, lang, page, query],
  );

  useDocumentTitle("Issue Discovery");
  usePageView();

  React.useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelected(undefined);
      }
    };
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, []);

  React.useEffect(() => {
    setSelected(undefined);
  }, [filter]);

  React.useEffect(() => {
    if (!isLoading) {
      window.scrollTo(0, 0);
    }
  }, [isLoading]);

  React.useEffect(() => {
    if (isLoading) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
  }, [isLoading]);

  React.useEffect(() => {
    if (selected) {
      dispatch?.({ type: "SHIFT" });
      return () => {
        dispatch?.({ type: "UNSHIFT" });
      };
    }
  }, [selected]);

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
              const date = t.date_time ? new Date(t.date_time) : undefined;
              return (
                <li
                  className={styles[`item${t === selected ? "-selected" : ""}`]}
                  key={i}
                  onClick={() => setSelected(t)}
                >
                  <span className={styles.title} title={summary}>
                    {summary}
                  </span>
                  <div className={styles.tags}>
                    {t.metadata?.app_version ? (
                      <Tag value={t.metadata?.app_version} />
                    ) : null}
                    {t.metadata?.screen_name ? (
                      <Tag value={t.metadata?.screen_name} />
                    ) : null}
                    {t.metadata?.course ? (
                      <Tag value={formatCourseId(t.metadata?.course)} />
                    ) : null}
                    {t.issue_key ? <Tag value={t.issue_key} /> : null}
                    {t.metadata?.platform === "android" ? (
                      <img
                        alt="Android"
                        className={styles.icon}
                        src={imagePlatformAndroid}
                      />
                    ) : t.metadata?.platform === "ios" ? (
                      <img
                        alt="iOS"
                        className={styles.icon}
                        src={imagePlatformApple}
                      />
                    ) : t.metadata?.platform === "web" ? (
                      <img
                        alt="Web"
                        className={styles.icon}
                        src={imagePlatformWeb}
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
              onRequestClose={() => setSelected(undefined)}
              ticket={selected}
            />,
            document.getElementById("aside") as HTMLElement,
          )
        : null}
    </>
  );
};

export default Discovery;
