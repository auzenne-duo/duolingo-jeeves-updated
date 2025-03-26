import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";

import { formatReadableDate, toDateString } from "../../util";
import {
  getQualityReportForArea,
  getQualityScoreForAreaDateRange,
} from "api/jeeves";
import { type DateRangeChangeEvent } from "components/DateRangeInput";
import NamedSection from "components/NamedSection";
import Table from "components/Table";
import TabsNav from "components/TabsNav";
import Tag from "components/Tag";
import Ticket from "components/Ticket";
import TicketList from "components/TicketList";
import QualityGraph from "components/quality-report/QualityGraph";
import styles from "components/quality-report/QualityReportForArea.module.scss";
import ScoreChange from "components/quality-report/ScoreChange";
import useDocumentTitle from "components/useDocumentTitle";
import useTicketAside from "components/useTicketAside";
import useTicketQuery from "components/useTicketQuery";
import useTicketSelection, {
  LIST_ID_PROP,
} from "components/useTicketSelection";
import AppStateContext from "contexts/AppStateContext";

const MAX_LINKED_ISSUES = 200;

const PLATFORM_MAP: Record<JSONAPI.Platform, string> = {
  Android: "DLAA",
  Web: "DLAW",
  iOS: "DLAI",
};

interface Props {
  area: string;
  team?: string;
  pillar: string;
}

const QualityReportForArea = ({ area, team, pillar }: Props) => {
  const location = useLocation();

  const [, dispatch] = React.useContext(AppStateContext);
  const [visibleTraces, setVisibleTraces] = React.useState<string[]>([
    "Overall",
  ]);

  useDocumentTitle(`${pillar}: ${area} Quality Report`);

  const { data, isLoading } = useQuery(["quality-report", area], () =>
    getQualityReportForArea(area),
  );

  const [dateRange, setDateRange] = React.useState<{ from: Date; to: Date }>({
    from: new Date(),
    to: new Date(),
  });

  const report = React.useMemo(
    () => (team ? data?.teams.find(t => t.title === team) : data),
    [data, team],
  );

  const showTicketsFrom = visibleTraces.includes("Overall")
    ? []
    : [...visibleTraces].sort();

  const ticketFilter = (t: JSONAPI.Ticket) =>
    !showTicketsFrom.length ||
    (t.platform !== undefined &&
      showTicketsFrom.includes(PLATFORM_MAP[t.platform]));

  const mostReported = report?.max_dupes_issues
    .filter(ticketFilter)
    .slice(0, 5);

  const highestPriority = report?.max_priority_issues
    .filter(ticketFilter)
    .slice(0, 5);

  const topDesign = report?.design_quality_issues
    .filter(ticketFilter)
    .slice(0, 5);

  const teams = React.useMemo(() => data?.teams.map(t => t.title), [data]);
  const tickets = [
    ...(mostReported?.map(t => ({ ...t, [LIST_ID_PROP]: "reported" })) ?? []),
    ...(highestPriority?.map(t => ({ ...t, [LIST_ID_PROP]: "priority" })) ??
      []),
    ...(topDesign?.map(t => ({ ...t, [LIST_ID_PROP]: "design" })) ?? []),
  ];

  const [id, setId, { listId: listIdOfSelection }] =
    useTicketSelection(tickets);
  useTicketAside(id);

  const { data: selected } = useTicketQuery(id);

  const handleClick = (t: JSONAPI.Ticket, listId: string) => {
    if (t.jeeves_uid === selected?.jeeves_uid && listId === listIdOfSelection) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid, listId);
    }
  };

  const handleDateRangeChange = (e: DateRangeChangeEvent) => {
    if (e.from && e.to) {
      setDateRange({ from: e.from, to: e.to });
    } else if (e.from) {
      setDateRange({ ...dateRange, from: e.from });
    } else if (e.to) {
      setDateRange({ ...dateRange, to: e.to });
    }
  };

  const isHistoricDateRangeSelected = (
    range: { from: Date; to: Date },
    rep: JSONAPI.DetailedQualityReport | undefined,
  ): boolean => {
    if (!rep) {
      return false;
    }

    // converting to dates first to avoid time zone issues
    const isDiffFromDate =
      toDateString(range.from) !== toDateString(new Date(rep.start_date));
    const isDiffToDate =
      toDateString(range.to) !== toDateString(new Date(rep.end_date));
    const isInitialFromDate =
      toDateString(range.from) === toDateString(new Date());
    const isInitialToDate = toDateString(range.to) === toDateString(new Date());

    return (
      !isInitialFromDate && !isInitialToDate && (isDiffFromDate || isDiffToDate)
    );
  };

  const {
    data: scoreHistory,
    isLoading: isLoadingScoreHist,
    isError: isErrorLoadingScoreHistory,
  } = useQuery(
    ["quality-score-history", area, team, dateRange, report],
    () =>
      getQualityScoreForAreaDateRange(
        team ?? area,
        dateRange.from,
        dateRange.to,
      ),
    {
      enabled: isHistoricDateRangeSelected(dateRange, report),
    },
  );

  // is loading is true when enabled is false, so need to check if enabled is set with loading
  // todo: v5 of react-query may make it unnecessary to check if the query is enabled, revisit then
  const isLoadingScoreHistory =
    isLoadingScoreHist && isHistoricDateRangeSelected(dateRange, report);

  React.useEffect(() => {
    // reset date range when report changes
    if (report) {
      setDateRange({
        from: new Date(report.start_date),
        to: new Date(report.end_date),
      });
    }
  }, [report]);

  return report ? (
    <>
      <TabsNav
        className={styles.tabs}
        tabs={[
          // There are some teams don't belong to a specific area, make an exception case here
          ...(area.startsWith("no_area")
            ? []
            : [
                {
                  href: `${location.pathname}?pillar=${encodeURIComponent(pillar)}&area=${encodeURIComponent(area)}`,
                  isActive: team === undefined,
                  name: "Entire area",
                },
              ]),
          ...(teams?.map(t => ({
            href: `${location.pathname}?pillar=${encodeURIComponent(pillar)}&area=${encodeURIComponent(
              area,
            )}&team=${encodeURIComponent(t)}`,
            isActive: t === team,
            name: t,
          })) ?? []),
        ]}
      />
      <div className={styles.header}>
        <h1 className={styles.title}>{report.title} Quality Report</h1>
        <strong>Overall score: {report.overall_score}</strong>
        <a href={report.open_bugs_url}>
          {report.open_bugs_count} open bug reports
          {report.open_bugs_count > MAX_LINKED_ISSUES
            ? ` (link shows first ${MAX_LINKED_ISSUES})`
            : null}
        </a>
        <span>
          {formatReadableDate(new Date(report.start_date))} to{" "}
          {formatReadableDate(new Date(report.end_date))}
        </span>
      </div>
      <QualityGraph
        className={styles.graph}
        from={dateRange.from}
        isErrorLoading={isErrorLoadingScoreHistory}
        isLoading={isLoadingScoreHistory}
        onChangeDateRange={handleDateRangeChange}
        onLegendClick={trace =>
          setVisibleTraces(
            visibleTraces.includes(trace)
              ? visibleTraces.filter(t => t !== trace)
              : visibleTraces.concat(trace),
          )
        }
        scores={scoreHistory?.scores ?? report.scores}
        title="Quality scores over time"
        to={dateRange.to}
        visibleTraces={visibleTraces}
      />
      {report.recent_changes ? (
        <NamedSection
          className={styles.section}
          layout="grid"
          name={`Changes since ${formatReadableDate(
            new Date(report.recent_changes.previous_report_date_string),
          )}`}
        >
          <div>
            <div>
              <a href={report.recent_changes.resolved_issue_link}>
                {report.recent_changes.resolved_issue_count} resolved issue(s)
              </a>{" "}
              <ScoreChange
                value={report.recent_changes.change_due_to_resolved_issues}
              />
            </div>
            <div>
              <a href={report.recent_changes.added_issue_link}>
                {report.recent_changes.added_issue_count} added issue(s)
              </a>{" "}
              <ScoreChange
                value={report.recent_changes.change_due_to_added_issues}
              />
            </div>
          </div>
        </NamedSection>
      ) : null}
      <NamedSection
        className={styles.section}
        name={`Most reported issues${
          showTicketsFrom.length ? ` in ${showTicketsFrom.join(" and ")}` : ""
        }`}
      >
        <TicketList
          bordered={false}
          onClick={ticket => handleClick(ticket, "reported")}
          selectedId={listIdOfSelection === "reported" ? id : undefined}
          tickets={mostReported ?? []}
        />
      </NamedSection>
      <NamedSection
        className={styles.section}
        name={`Highest priority issues${
          showTicketsFrom.length ? ` in ${showTicketsFrom.join(" and ")}` : ""
        }`}
      >
        <TicketList
          bordered={false}
          onClick={ticket => handleClick(ticket, "priority")}
          selectedId={listIdOfSelection === "priority" ? id : undefined}
          showTags={["priority", "issue_key", "status", "assignee", "date"]}
          tickets={highestPriority ?? []}
        />
      </NamedSection>
      <NamedSection
        className={styles.section}
        name={`Top design issues${
          showTicketsFrom.length ? ` in ${showTicketsFrom.join(" and ")}` : ""
        }`}
      >
        <TicketList
          bordered={false}
          onClick={ticket => handleClick(ticket, "design")}
          selectedId={listIdOfSelection === "design" ? id : undefined}
          showTags={[
            "priority",
            "issue_key",
            "child_issues",
            "status",
            "assignee",
            "date",
          ]}
          tickets={topDesign ?? []}
        />
      </NamedSection>
      <NamedSection
        className={styles.section}
        collapsible={true}
        layout="grid"
        name="Appendix"
      >
        {report.features.length ? (
          <>
            <span>
              This report was compiled using issues with the following features:
            </span>
            <div className={styles.features}>
              {report.features.map(f => (
                <Tag key={f} text={f} value={f} />
              ))}
            </div>
          </>
        ) : null}
        <span>
          The Quality Reports{" "}
          <a href="https://duolingo.atlassian.net/wiki/spaces/DUO/pages/2492432385/Quality+Reports#Score-Formula">
            Score Formula
          </a>{" "}
          is available on Confluence.
        </span>
        <Table className={styles.table}>
          <thead>
            <tr>
              <th colSpan={report.score_breakdowns.length + 1}>
                Score breakdown
              </th>
            </tr>
            <tr>
              <th />
              {report.score_breakdowns.map((b, i) => (
                <th key={i}>{formatReadableDate(new Date(b.date))}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className={styles.strong}>Closed points</td>
              {report.score_breakdowns.map((b, i) => (
                <td className={styles.strong} key={i}>
                  {b.closed_points}
                </td>
              ))}
            </tr>
            <tr>
              <td className={styles.strong}>Open points</td>
              {report.score_breakdowns.map((b, i) => (
                <td className={styles.strong} key={i}>
                  {b.open_points}
                </td>
              ))}
            </tr>
            {report.score_breakdowns[0].quality_score_type_counts.map(
              (q, i) => (
                <tr key={i}>
                  <td>{q.label}</td>
                  {report.score_breakdowns.map((b, j) => (
                    <td key={j}>
                      {b.quality_score_type_counts[i].points} (
                      {b.quality_score_type_counts[i].count})
                      {b.quality_score_type_counts[i].duplicate_bonus_points
                        ? ` + ${b.quality_score_type_counts[i].duplicate_bonus_points} duplicate bonus`
                        : null}
                    </td>
                  ))}
                </tr>
              ),
            )}
          </tbody>
          <tfoot>
            <tr>
              <td className={styles.strong}>Score (# issues)</td>
              {report.score_breakdowns.map((b, i) => (
                <td className={styles.strong} key={i}>
                  {b.overall_score} ({b.num_issues})
                </td>
              ))}
            </tr>
          </tfoot>
        </Table>
      </NamedSection>
      {selected
        ? createPortal(
            <Ticket
              className={styles.ticket}
              // Don't reuse the component for different tickets as it's stateful.
              key={selected.jeeves_uid}
              onRequestClose={() => setId(undefined)}
              ticket={selected}
            />,
            document.getElementById("aside") as HTMLElement,
          )
        : null}
    </>
  ) : isLoading ? null : (
    <span>There&apos;s no report data available for the selected filters.</span>
  );
};

export default QualityReportForArea;
