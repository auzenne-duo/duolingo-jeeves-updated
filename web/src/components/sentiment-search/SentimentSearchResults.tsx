import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { sentimentSearch } from "api/jeeves";
import SentimentGraph from "components/sentiment-search/SentimentGraph";
import styles from "components/sentiment-search/SentimentSearchResults.module.scss";
import SentimentSearchTable from "components/sentiment-search/SentimentSearchTable";
import useSearchParams from "components/useSearchParams";
import AppStateContext from "contexts/AppStateContext";

const SentimentSearchResults = () => {
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);

  const query = search.get("q") ?? "";

  const { data, error, isLoading } = useQuery(["sentiment-search", query], () =>
    sentimentSearch(query),
  );

  const docs = data?.results;
  const numResults = docs?.length ?? 0;

  React.useEffect(() => {
    if (data) {
      dispatch?.({
        numResults,
        timestamp: window.performance.now(),
        type: "SEARCH_END",
      });
    }
  }, [data, dispatch, numResults]);

  return isLoading ? (
    <span>Loading results from GPT...</span>
  ) : data ? (
    <>
      {data.positive_bucket &&
        data.positive_bucket.length > 0 &&
        data.negative_bucket &&
        data.negative_bucket.length > 0 && (
          <div className={styles.trend}>
            <SentimentGraph
              negativeBucket={data.negative_bucket}
              positiveBucket={data.positive_bucket}
            />
          </div>
        )}
      {data.results && data.results.length > 0 && (
        <SentimentSearchTable docs={data.results} />
      )}
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

export default SentimentSearchResults;
