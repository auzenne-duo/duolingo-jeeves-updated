import * as React from "react";
import { useParams } from "react-router-dom";

import { getSpikes } from "api";
import { AppDispatch } from "components/App";
import SpikeTable from "components/SpikeTable";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDateRangeFilter from "components/useDateRangeFilter";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const Spike = () => {
  const { from, to } = useDateRangeFilter({ daysAgo: 3 });
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const search = useSearchParams();

  const dispatch = React.useContext(AppDispatch);

  const filter = search.get("filter") ?? "ALL_SPIKES";

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    async () =>
      (
        await getSpikes(lang, {
          end_date: to,
          spike_category: filter as JSONAPI.SpikeCategory,
          start_date: from,
        })
      ).reverse(),
    [filter, from?.valueOf(), lang, to?.valueOf()],
  );

  useDocumentTitle("Spike Detector");
  usePageView();

  React.useEffect(() => {
    if (isLoading) {
      dispatch?.({ type: "LOADING" });
      return () => {
        dispatch?.({ type: "LOADED" });
      };
    }
  }, [isLoading]);

  return (
    <>
      {spikes?.map((o, i) => (
        <SpikeTable date={o.date} key={i} language={lang} spikes={o.spikes} />
      ))}
    </>
  );
};

export default Spike;
