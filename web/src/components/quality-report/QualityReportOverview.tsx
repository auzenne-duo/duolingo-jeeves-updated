import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";
import { getButtonClassName } from "web-ui";

import { getQualityReport } from "api/jeeves";
import cn from "classnames";
import QualityGraph from "components/quality-report/QualityGraph";
import styles from "components/quality-report/QualityReportOverview.scss";
import useDocumentTitle from "components/useDocumentTitle";
import usePageLanguage from "components/usePageLanguage";

const QualityReportOverview = () => {
  const lang = usePageLanguage();

  useDocumentTitle("Quality Report");

  const { data: report } = useQuery(["quality-report"], () =>
    getQualityReport(),
  );

  return report ? (
    <div className={styles.grid}>
      {report?.areas.map(a => (
        <Link
          className={cn(
            getButtonClassName({ variant: "stroke" }),
            styles.button,
          )}
          key={a.title}
          to={`/${lang}/quality-report?area=${encodeURIComponent(a.title)}`}
        >
          <QualityGraph
            className={styles.graph}
            overallOnly={true}
            scores={a.scores}
            title={a.title}
          />
        </Link>
      ))}
    </div>
  ) : null;
};

export default QualityReportOverview;
