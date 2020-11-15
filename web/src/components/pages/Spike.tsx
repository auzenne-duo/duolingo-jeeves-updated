import * as React from "react";
import { useParams } from "react-router-dom";

import { getSpikes } from "api";
import { LanguageId } from "components/LanguagePicker";
import Loading from "components/Loading";
import SpikeTable from "components/SpikeTable";
import { useAwaitedValue } from "components/useAwaitedValue";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";

const Spike = () => {
  const { lang } = useParams<{ lang: LanguageId }>();

  const [spikes, isLoading] = useAwaitedValue(
    undefined,
    () => getSpikes(lang),
    [lang],
  );

  useDocumentTitle("Spike Detector");
  usePageView();

  return (
    <>
      {isLoading ? (
        <Loading />
      ) : (
        Object.keys(spikes ?? {})
          .reverse()
          .map(date => (
            <SpikeTable
              date={date}
              key={date}
              language={lang}
              spikes={spikes?.[date] ?? []}
            />
          ))
      )}
    </>
  );
};

export default Spike;
