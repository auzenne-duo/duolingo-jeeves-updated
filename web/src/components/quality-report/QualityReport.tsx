import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";

import { encodeURLSearchParams } from "../../util";
import QualityReportForArea from "components/quality-report/QualityReportForArea";
import QualityReportOverview from "components/quality-report/QualityReportOverview";
import useSearchParams from "components/useSearchParams";

const QualityReport = () => {
  const history = useHistory();
  const location = useLocation();
  const search = useSearchParams();

  const area = search.get("area");
  const team = search.get("team");

  const handleTeamChange = (newValue: string) => {
    const params = new URLSearchParams(location.search);
    if (newValue === "-1") {
      params.delete("team");
    } else {
      params.set("team", newValue);
    }
    history.push({
      ...location,
      search: encodeURLSearchParams(params),
    });
  };

  return area ? (
    <QualityReportForArea
      area={area}
      onTeamChange={handleTeamChange}
      team={team ?? undefined}
    />
  ) : (
    <QualityReportOverview />
  );
};

export default QualityReport;
