import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";

import { getQualityReport } from "api/jeeves";
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
          key={a.title}
          to={`/${lang}/quality-report?area=${encodeURIComponent(a.title)}`}
        >
          <QualityGraph overallOnly={true} scores={a.scores} title={a.title} />
        </Link>
      ))}
    </div>
  ) : null;
};

export default QualityReportOverview;
