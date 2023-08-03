import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { createPortal } from "react-dom";
import type { Range } from "web-ui/util/highlight";

import { gptSearch } from "api/jeeves";
import Ticket from "components/Ticket";
import TicketList from "components/TicketList";
import styles from "components/gpt-search/GPTSearchResults.scss";
import useSearchParams from "components/useSearchParams";
import useTicketAside from "components/useTicketAside";
import useTicketQuery from "components/useTicketQuery";
import useTicketSelection from "components/useTicketSelection";
import AppStateContext from "contexts/AppStateContext";

const OPENING_TAG = "<b>";
const CLOSING_TAG = "</b>";

const getHighlightIndices = (html: string): Range[] => {
  const indices: Range[] = [];
  const exp = new RegExp(OPENING_TAG, "g");
  let opening;
  while ((opening = exp.exec(html)) !== null) {
    const closing = new RegExp(CLOSING_TAG).exec(
      html.slice(opening.index + OPENING_TAG.length),
    );
    if (closing) {
      indices.push([
        opening.index -
          (OPENING_TAG.length + CLOSING_TAG.length) * indices.length,
        opening.index +
          closing.index -
          1 -
          (OPENING_TAG.length + CLOSING_TAG.length) * indices.length,
      ]);
    } else {
      // No closing tag found; match until the end.
      indices.push([
        opening.index -
          (OPENING_TAG.length + CLOSING_TAG.length) * indices.length,
        html.length -
          1 -
          (OPENING_TAG.length + CLOSING_TAG.length) * indices.length -
          OPENING_TAG.length,
      ]);
    }
  }
  return indices;
};

const GPTSearchResults = () => {
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);

  const query = search.get("q") ?? "";

  const { data, error, isLoading } = useQuery(["gpt-search", query], () =>
    gptSearch(query),
  );

  const answer = data?.answer;
  const docs = data?.results;
  const numResults = docs?.length ?? 0;

  React.useEffect(() => {
    if (data) {
      dispatch?.({
        answer,
        numResults,
        timestamp: window.performance.now(),
        type: "SEARCH_END",
      });
    }
  }, [answer, data, dispatch, numResults]);

  // TODO (david.sawicki): return actual Jeeves documents from the backend.
  const tickets = React.useMemo(
    () =>
      docs?.map(
        (d): JSONAPI.Ticket => ({
          body_text: d.original_text.body_orig,
          data_source: d.origin as JSONAPI.DataSource,
          date_time: d.datetime,
          document_id: "",
          duolingo_metadata: {},
          header_text: d.original_text.title,
          jeeves_uid: d.uid,
          shake_to_report_category: "" as JSONAPI.ShakeToReportCategory,
        }),
      ),
    [docs],
  );

  // TODO (renspoesse): pass on pagination functions once implemented.
  // TODO (renspoesse): implement these hooks and the TicketList component
  //  for the new sentiment search views.
  const [id, setId] = useTicketSelection(tickets);
  useTicketAside(id);

  const { data: selected } = useTicketQuery(id);

  const highlight = React.useMemo(() => {
    const doc = docs?.find(d => selected && d.uid === selected.jeeves_uid);
    return doc ? getHighlightIndices(doc.original_text.body) : undefined;
  }, [docs, selected]);

  const handleClick = (t: JSONAPI.Ticket) => {
    if (t.jeeves_uid === selected?.jeeves_uid) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid);
    }
  };

  React.useEffect(() => {
    dispatch?.({ type: "HIDE_ASIDE" });
  }, [dispatch, query]);

  // Scrolls the page to the top when fresh query data is loaded.
  React.useEffect(() => {
    if (data) {
      window.scrollTo(0, 0);
    }
  }, [data]);

  return isLoading ? (
    <span>Loading results from GPT...</span>
  ) : data && tickets ? (
    <>
      <span>{answer}</span>
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
      <TicketList onClick={handleClick} selectedId={id} tickets={tickets} />
      {selected
        ? createPortal(
            <Ticket
              className={styles.ticket}
              highlight={highlight}
              // Don't reuse the component for different tickets as it's stateful.
              key={selected.jeeves_uid}
              onRequestClose={() => setId(undefined)}
              ticket={selected}
            />,
            document.getElementById("aside") as HTMLElement,
          )
        : null}
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
