import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { createPortal } from "react-dom";
import { Card, CardRadioGroup } from "web-ui";

import { formatReadableDate } from "../../util";
import { getQualityReportForArea } from "api/jeeves";
import Table from "components/Table";
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

interface Props {
  area: string;
  onTeamChange: (newValue: string) => void;
  team?: string;
}

const QualityReportForArea = ({ area, onTeamChange, team }: Props) => {
  const [, dispatch] = React.useContext(AppStateContext);

  useDocumentTitle(`${area} Quality Report`);

  const { data } = useQuery(["quality-report", area], () =>
    getQualityReportForArea(),
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
      <CardRadioGroup
        className={styles.teams}
        onChange={e => onTeamChange(e.value)}
        value={team ?? "-1"}
      >
        <Card className={styles["team-card"]} role="radio" value="-1">
          Entire area
        </Card>
        {teams?.map(t => (
          <Card className={styles["team-card"]} key={t} role="radio" value={t}>
            {t}
          </Card>
        ))}
      </CardRadioGroup>
      <div className={styles.header}>
        <div className={styles["header-left"]}>
          <h1>{report.title} Quality Report</h1>
          <span>Overall score: {report.overall_score}</span>
        </div>
        <div className={styles["header-right"]}>
          <span>
            {formatReadableDate(new Date(report.start_date))} to{" "}
            {formatReadableDate(new Date(report.end_date))}
          </span>
          <a href={report.open_bugs_url}>
            {report.open_bugs_count} open bug reports
          </a>
        </div>
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
      <h2>Appendix</h2>
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
          {report.score_breakdowns[0].quality_score_type_counts.map((q, i) => (
            <tr key={i}>
              <td>{q.label}</td>
              {report.score_breakdowns.map((b, j) => (
                <td key={j}>
                  {b.quality_score_type_counts[i].points} (
                  {b.quality_score_type_counts[i].count})
                </td>
              ))}
            </tr>
          ))}
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
