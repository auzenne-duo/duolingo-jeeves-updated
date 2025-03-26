import { useQuery } from "@tanstack/react-query";
import cn from "classnames";
import * as React from "react";
import { Link } from "react-router-dom";
import { getButtonClassName } from "web-ui/legacy";

import { getQualityReport, getQualityReportOverview } from "api/jeeves";
import QualityGraph from "components/quality-report/QualityGraph";
import styles from "components/quality-report/QualityReportOverview.module.scss";
import useDocumentTitle from "components/useDocumentTitle";
import usePageLanguage from "components/usePageLanguage";

const QualityReportOverview = () => {
  const lang = usePageLanguage();

  useDocumentTitle("Quality Report");

  const { data: report, isLoading } = useQuery(["quality-report"], () =>
    getQualityReportOverview(),
  );

  return isLoading ? null : report ? (
    <div className={styles.grid}>
      {report?.pillars.map(a =>
        // We make exceptions for areas that don't fit into normal pillar structure
        // Areas under "Other" pillar get special handling since they are grouped differently in the UI
        // This includes teams like "Severin" that don't map cleanly to a single pillar
        // Rather than showing "Other" as its own pillar, we display its areas alongside regular pillars
        a.title.startsWith("Other") ? (
          <OtherQualityReports key={a.title} pillar={a.title} />
        ) : (
          <Link
            className={cn(
              getButtonClassName({ variant: "stroke" }),
              styles.button,
            )}
            key={a.title}
            to={`/${lang}/quality-report?pillar=${encodeURIComponent(a.title)}`}
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
  pillar: string;
  key: string;
}

const OtherQualityReports = ({ pillar }: PropsTeam) => {
  const lang = usePageLanguage();

  const { data: teamReport } = useQuery(["quality-report-area", pillar], () =>
    getQualityReport(pillar),
  );

  if (!teamReport) {
    return null;
  }

  return (
    <>
      {teamReport?.areas.map(area =>
        // "Misc" is a special area that contains unowned STR menu items and bug reports
        // Rather than showing these in the UI, we filter them out to avoid confusion
        area?.title === "Misc" ? null : (
          <Link
            className={cn(
              getButtonClassName({ variant: "stroke" }),
              styles.button,
            )}
            key={area.title}
            to={`/${lang}/quality-report?pillar=${pillar}&area=${encodeURIComponent(area.title)}`}
          >
            <QualityGraph
              className={styles.graph}
              scores={area.scores}
              title={area.title}
              visibleTraces={["Overall"]}
            />
          </Link>
        ),
      )}
    </>
  );
};

export default QualityReportOverview;
