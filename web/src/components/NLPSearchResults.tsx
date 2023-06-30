import * as React from "react";
import { useQuery } from "react-query";

import { nlpSearch } from "api/jeeves";
import useSearchParams from "components/useSearchParams";
import styles from "styles/NLPSearchResults.scss";

import NLPSearchTable from "./NLPSearchTable";

const NLPSearchResults = () => {
  const search = useSearchParams();
  const query = search.get("q") ?? "";

  const queryKey = ["nlp_search", query];

  const { data, error, isLoading } = useQuery<JSONAPI.NLPSearchResponse>(
    queryKey,
    () => nlpSearch(query),
    { keepPreviousData: true },
  );

  return isLoading ? (
    <span className={styles.loading}>Loading results from GPT...</span>
  ) : data ? (
    <>
      <span className={styles.answer}>{data.answer}</span>
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
      <NLPSearchTable docs={data.results} />
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

export default NLPSearchResults;
