import * as React from "react";

import QualityReportForArea from "components/quality-report/QualityReportForArea";
import QualityReportOverview from "components/quality-report/QualityReportOverview";
import useSearchParams from "components/useSearchParams";

const QualityReport = () => {
  const search = useSearchParams();

  const area = search.get("area");
  const team = search.get("team");

  return area ? (
    <QualityReportForArea area={area} team={team ?? undefined} />
  ) : (
    <QualityReportOverview />
  );
};

export default QualityReport;
