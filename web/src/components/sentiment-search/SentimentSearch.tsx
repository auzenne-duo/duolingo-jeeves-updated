import * as React from "react";

import SentimentSearchResults from "components/sentiment-search/SentimentSearchResults";
import useDocumentTitle from "components/useDocumentTitle";
import useSearchParams from "components/useSearchParams";

const SentimentSearch = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("Sentiment Search");

  return query ? (
    <SentimentSearchResults />
  ) : (
    <span>Search for anything about Duolingo.</span>
  );
};
export default SentimentSearch;
