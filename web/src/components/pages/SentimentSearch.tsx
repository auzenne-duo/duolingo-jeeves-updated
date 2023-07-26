import * as React from "react";

import SentimentSearchResults from "components/SentimentSearchResults";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const SentimentSearch = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("Sentiment Search");
  usePageView();

  React.useEffect(() => {
    ga("send", "event", {
      eventAction: "search",
      eventCategory: "sentiment",
      eventLabel: query,
    });
  }, [query]);

  return query ? (
    <SentimentSearchResults />
  ) : (
    <span>Search for anything about Duolingo.</span>
  );
};
export default SentimentSearch;
