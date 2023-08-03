import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { spikeToStrCategory } from "../../util";
import { getSpikeStats } from "api/jeeves";
import ConfirmationStatsTable from "components/spike-stats/ConfirmationStatsTable";
import SpikeWordStatsTable from "components/spike-stats/SpikeWordStatsTable";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageLanguage from "components/usePageLanguage";
import useSearchParams from "components/useSearchParams";

const SpikeStats = () => {
  const { from, to } = useDateRangeFilter({ monthsAgo: 3 });
  const lang = usePageLanguage();
  const search = useSearchParams();

  const filter = search.get("filter") ?? "ALL_SPIKES";

  const { data } = useQuery(["spike-stats", { filter, from, lang, to }], () =>
    getSpikeStats(lang, {
      end_date: to,
      spike_category: filter,
      start_date: from,
    }),
  );

  useDocumentTitle("Spike Stats");

  return data ? (
    <>
      <ConfirmationStatsTable spikeStats={data} />
      <SpikeWordStatsTable
        language={lang}
        linkFilter={spikeToStrCategory(filter)}
        spikeStats={data}
      />
    </>
  ) : null;
};

export default SpikeStats;
