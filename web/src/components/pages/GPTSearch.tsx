import * as React from "react";

import GPTSearchResults from "components/GPTSearchResults";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";
import useSearchParams from "components/useSearchParams";

const GPTSearch = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("GPT Search");
  usePageView();

  React.useEffect(() => {
    ga("send", "event", {
      eventAction: "search",
      eventCategory: "GPT",
      eventLabel: query,
    });
  }, [query]);

  return query ? (
    <GPTSearchResults />
  ) : (
    <span>Search for anything about Duolingo.</span>
  );
};

export default GPTSearch;
