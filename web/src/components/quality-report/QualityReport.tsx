import * as React from "react";

import QualityReportForArea from "components/quality-report/QualityReportForArea";
import QualityReportOverview from "components/quality-report/QualityReportOverview";
import QualityReportOverviewArea from "components/quality-report/QualityReportOverviewArea";
import useSearchParams from "components/useSearchParams";
import track from "track";

const QualityReport = () => {
  const search = useSearchParams();

  const pillar = search.get("pillar");
  const area = search.get("area");
  const team = search.get("team");
  const utmSource = search.get("utm_source");

  React.useEffect(() => {
    track("quality_reports_view", {
      quality_report_area: area ?? undefined,
      quality_report_pillar: pillar ?? undefined,
      quality_report_team: team ?? undefined,
      utm_source: utmSource ?? undefined,
    });
  }, [area, pillar, team, utmSource]);

  return pillar ? (
    area ? (
      <QualityReportForArea
        area={area}
        pillar={pillar}
        team={team ?? undefined}
      />
    ) : (
      <QualityReportOverviewArea pillar={pillar} />
    )
  ) : (
    <QualityReportOverview />
  );
};

export default QualityReport;
