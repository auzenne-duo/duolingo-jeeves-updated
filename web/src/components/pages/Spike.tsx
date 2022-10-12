import { spikeToStrCategory } from "util";

import * as React from "react";
import { useQuery } from "react-query";
import { useParams } from "react-router-dom";

import { getSpikes } from "api/jeeves";
import SpikeTable from "components/SpikeTable";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const Spike = () => {
  const { from, to } = useDateRangeFilter({ daysAgo: 3 });
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const search = useSearchParams();

  const filter = search.get("filter") ?? "ALL_SPIKES";

  const { data } = useQuery(
    ["spikes", { filter, from, lang, to }],
    () =>
      getSpikes(lang, {
        end_date: to,
        spike_category: filter,
        start_date: from,
      }),
    {
      select: d => d.slice().reverse(),
    },
  );

  useDocumentTitle("Spike Detector");
  usePageView();

  return (
    <>
      {data?.map((o, i) => (
        <SpikeTable
          date={o.date}
          key={i}
          language={lang}
          linkFilter={spikeToStrCategory(filter)}
          spikeCategory={filter}
          spikes={o.spikes}
        />
      ))}
    </>
  );
};

export default Spike;
