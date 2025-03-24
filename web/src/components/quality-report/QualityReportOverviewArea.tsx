import { useQuery } from "@tanstack/react-query";
import cn from "classnames";
import * as React from "react";
import { Link } from "react-router-dom";
import { getButtonClassName } from "web-ui/legacy";

import { getQualityReport, getQualityReportTeam } from "api/jeeves";
import QualityGraph from "components/quality-report/QualityGraph";
import styles from "components/quality-report/QualityReportOverview.module.scss";
import useDocumentTitle from "components/useDocumentTitle";
import usePageLanguage from "components/usePageLanguage";

interface Props {
  pillar: string;
}

const QualityReportOverviewArea = ({ pillar }: Props) => {
  const lang = usePageLanguage();

  useDocumentTitle("Quality Report Overview Area");

  const { data: report } = useQuery(["quality-report", pillar], () =>
    getQualityReport(pillar),
  );

  return report ? (
    <div className={styles.grid}>
      {report?.areas.map(a =>
        // We make exceptions for areas that don't fit into normal area structure
        // Areas under "no_area" get special handling since they are grouped differently in the UI
        // This includes teams like "no_area_monetization" that don't have a clear Area name
        // Rather than showing "no_area" as its own area, we display its teams alongside regular areas
        a.title.startsWith("no_area") ? (
          <TeamQualityReports area={a.title} key={a.title} pillar={pillar} />
        ) : (
          <Link
            className={cn(
              getButtonClassName({ variant: "stroke" }),
              styles.button,
            )}
            key={a.title}
            to={`/${lang}/quality-report?pillar=${pillar}&area=${encodeURIComponent(a.title)}`}
          >
            <QualityGraph
              className={styles.graph}
              scores={a.scores}
              title={a.title}
              visibleTraces={["Overall"]}
            />
          </Link>
        ),
      )}
    </div>
  ) : null;
};

interface PropsTeam {
  area: string;
  pillar: string;
}

const TeamQualityReports = ({ pillar, area }: PropsTeam) => {
  const lang = usePageLanguage();

  const { data: teamReport } = useQuery(
    ["quality-report-team", pillar, area],
    () => getQualityReportTeam(pillar, area),
  );

  if (!teamReport) {
    return null;
  }

  return (
    <>
      {teamReport?.teams.map(team => (
        <Link
          className={cn(
            getButtonClassName({ variant: "stroke" }),
            styles.button,
          )}
          key={team.title}
          to={`/${lang}/quality-report?pillar=${pillar}&area=${area}&team=${encodeURIComponent(team.title)}`}
        >
          <QualityGraph
            className={styles.graph}
            scores={team.scores}
            title={team.title}
            visibleTraces={["Overall"]}
          />
        </Link>
      ))}
    </>
  );
};

export default QualityReportOverviewArea;
