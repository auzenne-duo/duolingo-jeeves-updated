import * as React from "react";

import NLPSearchResults from "components/NLPSearchResults";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const NLPSearch = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("NLP Search");
  usePageView();

  React.useEffect(() => {
    ga("send", "event", {
      eventAction: "search",
      eventCategory: "NLP",
      eventLabel: query,
    });
  }, [query]);

  return query ? (
    <NLPSearchResults />
  ) : (
    <span>
      Ask any question about Jeeves data in the search box and press
      &quot;enter&quot;.
    </span>
  );
};

export default NLPSearch;
