import * as React from "react";
import { useQuery } from "react-query";
import { useParams } from "react-router-dom";

import { getConfirmationStats } from "api/jeeves";
import ConfirmationTable from "components/ConfirmationTable";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const ConfirmationStats = () => {
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();
  const search = useSearchParams();

  const filter = (search.get("filter") ??
    "ALL_SPIKES") as JSONAPI.SpikeCategory;

  const { data } = useQuery(["confirmation-stats", { filter, lang }], () =>
    getConfirmationStats(lang, {
      spike_category: filter,
    }),
  );

  useDocumentTitle("Spike Confirmation Stats");
  usePageView();

  return data ? <ConfirmationTable confirmationStats={data} /> : null;
};

export default ConfirmationStats;
