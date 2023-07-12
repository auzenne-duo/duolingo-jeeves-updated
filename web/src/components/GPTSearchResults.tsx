import * as React from "react";
import { useQuery } from "react-query";

import { gptSearch } from "api/jeeves";
import GPTSearchTable from "components/GPTSearchTable";
import useSearchParams from "components/useSearchParams";
import styles from "styles/GPTSearchResults.scss";

const GPTSearchResults = () => {
  const search = useSearchParams();

  const query = search.get("q") ?? "";
  const queryKey = ["gpt-search", query];

  const { data, error, isLoading } = useQuery<JSONAPI.GPTSearchResponse>(
    queryKey,
    () => gptSearch(query),
    { keepPreviousData: true },
  );

  return isLoading ? (
    <span>Loading results from GPT...</span>
  ) : data ? (
    <>
      <span>{data.answer}</span>
      {data.lucene_query && data.lucene_query.length > 0 && (
        <div>
          OpenSearch filters applied:
          <ul>
            {data.lucene_query.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
      <GPTSearchTable docs={data.results} />
    </>
  ) : error ? (
    <span className={styles.error}>
      Sorry, something went wrong. No data was fetched from GPT.
    </span>
  ) : (
    <span className={styles.error}>
      Sorry, something went wrong. No data was returned from the Jeeves API.
    </span>
  );
};

export default GPTSearchResults;
