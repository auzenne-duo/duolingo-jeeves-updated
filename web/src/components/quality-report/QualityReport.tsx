import * as React from "react";

import QualityReportForArea from "components/quality-report/QualityReportForArea";
import QualityReportOverview from "components/quality-report/QualityReportOverview";
import useSearchParams from "components/useSearchParams";
import track from "track";

const QualityReport = () => {
  const search = useSearchParams();

  const area = search.get("area");
  const team = search.get("team");
  const utmSource = search.get("utm_source");

  React.useEffect(() => {
    track("quality_reports_view", {
      quality_report_area: area ?? undefined,
      quality_report_team: team ?? undefined,
      utm_source: utmSource ?? undefined,
    });
  }, [area, team, utmSource]);

  return area ? (
    <QualityReportForArea area={area} team={team ?? undefined} />
  ) : (
    <QualityReportOverview />
  );
};

export default QualityReport;
