import * as React from "react";

import GPTSearchResults from "components/gpt-search/GPTSearchResults";
import useDocumentTitle from "components/useDocumentTitle";
import useSearchParams from "components/useSearchParams";

const GPTSearch = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";

  useDocumentTitle("GPT Search");

  return query ? (
    <GPTSearchResults />
  ) : (
    <span>Search for anything about Duolingo.</span>
  );
};

export default GPTSearch;
