import * as React from "react";
import { useParams } from "react-router-dom";

import { getSpikes } from "api";
import { AppDispatch } from "components/App";
import { LanguageId } from "components/LanguagePicker";
import SpikeTable from "components/SpikeTable";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";

const Spike = () => {
  const { lang } = useParams<{ lang: LanguageId }>();

  const dispatch = React.useContext(AppDispatch);

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    () => getSpikes(lang),
    [lang],
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
