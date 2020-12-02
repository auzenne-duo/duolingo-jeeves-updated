import * as React from "react";
import { useParams } from "react-router-dom";

import { SpikeCategory, getSpikes } from "api";
import { AppDispatch } from "components/App";
import { LanguageId } from "components/LanguagePicker";
import SpikeTable from "components/SpikeTable";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";
import { midnight } from "util";

const Spike = () => {
  const { lang } = useParams<{ lang: LanguageId }>();
  const search = useSearchParams();

  const dispatch = React.useContext(AppDispatch);

  const oneWeekAgo = midnight(new Date());
  oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

  const filter = search.get("filter") ?? "ALL_SPIKES";
  const from = search.get("from")
    ? new Date(search.get("from") as string)
    : oneWeekAgo;
  const to = search.get("to")
    ? new Date(search.get("to") as string)
    : undefined;

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    () =>
      getSpikes(lang, {
        end_date: to,
        spike_category: filter as SpikeCategory,
        start_date: from,
      }),
    [filter, from?.toJSON(), lang, to?.toJSON()],
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
      {Object.keys(spikes ?? {})
        .reverse()
        .map(date => (
          <SpikeTable
            date={date}
            key={date}
            language={lang}
            spikes={spikes?.[date] ?? []}
          />
        ))}
    </>
  );
};

export default Spike;
