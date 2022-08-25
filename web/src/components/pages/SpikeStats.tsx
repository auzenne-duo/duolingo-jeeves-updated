import { spikeToStrCategory } from "util";

import * as React from "react";
import { useQuery } from "react-query";
import { useParams } from "react-router-dom";

import { getSpikeStats } from "api/jeeves";
import ConfirmationStatsTable from "components/ConfirmationStatsTable";
import SpikeWordStatsTable from "components/SpikeWordStatsTable";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const SpikeStats = () => {
  const { from, to } = useDateRangeFilter({ monthsAgo: 3 });
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const search = useSearchParams();

  const filter = (search.get("filter") ??
    "ALL_SPIKES") as JSONAPI.SpikeCategory;

  const { data } = useQuery(["spike-stats", { filter, from, lang, to }], () =>
    getSpikeStats(lang, {
      end_date: to,
      spike_category: filter,
      start_date: from,
    }),
  );

  useDocumentTitle("Spike Stats");
  usePageView();

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
