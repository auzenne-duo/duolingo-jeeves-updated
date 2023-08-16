import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { Button } from "web-ui";

import { formatReadableDate } from "../../util";
import { getQualityReportForArea } from "api/jeeves";
import Table from "components/Table";
import TabsNav from "components/TabsNav";
import Tag from "components/Tag";
import Ticket from "components/Ticket";
import TicketList from "components/TicketList";
import QualityGraph from "components/quality-report/QualityGraph";
import styles from "components/quality-report/QualityReportForArea.scss";
import useDocumentTitle from "components/useDocumentTitle";
import useTicketAside from "components/useTicketAside";
import useTicketQuery from "components/useTicketQuery";
import useTicketSelection from "components/useTicketSelection";
import AppStateContext from "contexts/AppStateContext";
import imageCaret from "images/caret.svg";

interface Props {
  area: string;
  team?: string;
}

const QualityReportForArea = ({ area, team }: Props) => {
  const location = useLocation();

  const [, dispatch] = React.useContext(AppStateContext);
  const [isAppendixOpen, setIsAppendixOpen] = React.useState(false);

  useDocumentTitle(`${area} Quality Report`);

  const { data } = useQuery(["quality-report", area], () =>
    getQualityReportForArea(area),
  );

  const report = React.useMemo(
    () => (team ? data?.teams.find(t => t.title === team) : data),
    [data, team],
  );

  const teams = React.useMemo(() => data?.teams.map(t => t.title), [data]);
  const tickets = React.useMemo(
    () =>
      report ? [...report.max_dupes_issues, ...report.max_priority_issues] : [],
    [report],
  );

  const [id, setId] = useTicketSelection(tickets);
  useTicketAside(id);

  const { data: selected } = useTicketQuery(id);

  const handleClick = (t: JSONAPI.Ticket) => {
    if (t.jeeves_uid === selected?.jeeves_uid) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid);
    }
  };

  return report ? (
    <>
      <TabsNav
        className={styles.tabs}
        tabs={[
          {
            href: `${location.pathname}?area=${encodeURIComponent(area)}`,
            isActive: team === undefined,
            name: "Entire area",
          },
          ...(teams?.map(t => ({
            href: `${location.pathname}?area=${encodeURIComponent(
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
        </a>
        <span>
          {formatReadableDate(new Date(report.start_date))} to{" "}
          {formatReadableDate(new Date(report.end_date))}
        </span>
      </div>
      <QualityGraph
        className={styles.graph}
        scores={report.scores}
        title="Quality scores over time"
      />
      <h2>Most reported issues</h2>
      {report.max_dupes_issues.length ? (
        <TicketList
          onClick={handleClick}
          selectedId={id}
          tickets={report.max_dupes_issues}
        />
      ) : (
        <span>No issues have been found.</span>
      )}
      <h2>Highest priority issues</h2>
      {report.max_priority_issues.length ? (
        <TicketList
          onClick={handleClick}
          selectedId={id}
          tickets={report.max_priority_issues}
        />
      ) : (
        <span>No issues have been found.</span>
      )}
      <h2>Top design issues</h2>
      {report.visual_polish_issues.length ? (
        <TicketList
          onClick={handleClick}
          selectedId={id}
          tickets={report.visual_polish_issues}
        />
      ) : (
        <span>No issues have been found.</span>
      )}
      <Button
        className={styles.toggle}
        onClick={() => setIsAppendixOpen(value => !value)}
      >
        <h2>Appendix</h2>
        <img
          alt={isAppendixOpen ? "Hide appendix" : "Show appendix"}
          className={isAppendixOpen ? styles["caret-up"] : styles.caret}
          src={imageCaret}
        />
      </Button>
      {isAppendixOpen ? (
        <div className={styles.appendix}>
          <span>
            This report was compiled using issues with the following features:
          </span>
          <div className={styles.features}>
            {report.features?.map(f => (
              <Tag key={f} text={f} value={f} />
            ))}
          </div>
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
        </div>
      ) : null}
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
  ) : (
    <span>There&apos;s no report data available for the selected filters.</span>
  );
};

export default QualityReportForArea;
