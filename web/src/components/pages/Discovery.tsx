import { format, formatISO, isThisYear, isToday } from "date-fns";
import * as React from "react";
import { createPortal } from "react-dom";
import { useLocation, useParams } from "react-router-dom";

import { getTickets } from "api";
import { AppDispatch } from "components/App";
import Pagination from "components/Pagination";
import Table from "components/Table";
import Ticket from "components/Ticket";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import styles from "styles/pages/Discovery.scss";
import {
  encodeURLSearchParams,
  formatCourseId,
  formatPlatform,
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
      <Table className={styles.table}>
        <thead>
          <tr>
            <th style={{ width: "40%" }}>Summary</th>
            <th style={{ width: 120 }}>Date</th>
            <th>Screen</th>
            <th>Platform</th>
            <th>App</th>
            <th>Course</th>
          </tr>
        </thead>
        <tbody>
          {tickets?.map((t, i) => {
            const summary =
              t.data_source === "JIRA"
                ? t.header_text
                : t.body_text?.trim().split("\n")[0];
            const date = t.date_time ? new Date(t.date_time) : undefined;
            return (
              <tr
                className={t === selected ? styles.selected : undefined}
                key={i}
                onClick={() => setSelected(t)}
              >
                <td title={summary}>{summary}</td>
                <td
                  className={styles.date}
                  title={date ? formatReadableDate(date) : undefined}
                >
                  {date ? formatDate(date) : null}
                </td>
                <td>{t.metadata?.screen_name}</td>
                <td>
                  {t.metadata?.platform
                    ? formatPlatform(t.metadata?.platform)
                    : null}
                </td>
                <td>{t.metadata?.app_version}</td>
                <td>
                  {t.metadata?.course
                    ? formatCourseId(t.metadata?.course)
                    : null}
                </td>
              </tr>
            );
          })}
        </tbody>
        {tickets?.length || !isLoading ? (
          <tfoot>
            <tr>
              <td colSpan={6}>
                {tickets?.length ? (
                  <div className={styles.pagination}>
                    {getPaginationString({
                      page,
                      perPage: PER_PAGE,
                      total: totalTickets,
                    })}
                  </div>
                ) : (
                  <span>Your search returned no results.</span>
                )}
              </td>
            </tr>
          </tfoot>
        ) : null}
      </Table>
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
