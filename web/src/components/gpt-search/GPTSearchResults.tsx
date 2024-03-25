import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { createPortal } from "react-dom";
import type { Range } from "web-ui/util/highlight";

import { gptSearch, gptSearchAnswer, gptSearchKnnResults } from "api/jeeves";
import NamedSection from "components/NamedSection";
import Table from "components/Table";
import Ticket from "components/Ticket";
import TicketList from "components/TicketList";
import styles from "components/gpt-search/GPTSearchResults.module.scss";
import useSearchParams from "components/useSearchParams";
import useTicketAside from "components/useTicketAside";
import useTicketQuery from "components/useTicketQuery";
import useTicketSelection, {
  LIST_ID_PROP,
} from "components/useTicketSelection";
import AppStateContext from "contexts/AppStateContext";

// Maps backend error messages to a more user-friendly format.
const ERROR_MESSAGES: Partial<Record<string, string>> = {
  "Timed out waiting for the k-NN search to finish.":
    "Timed out waiting for the search to finish.",
};

const OPENING_TAG = "<b>";
const CLOSING_TAG = "</b>";
const TAG_PAIR_LENGTH = OPENING_TAG.length + CLOSING_TAG.length;

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
        opening.index - TAG_PAIR_LENGTH * indices.length,
        opening.index + closing.index - 1 - TAG_PAIR_LENGTH * indices.length,
      ]);
    } else {
      // No closing tag found; match until the end.
      indices.push([
        opening.index - TAG_PAIR_LENGTH * indices.length,
        html.length - 1 - TAG_PAIR_LENGTH * indices.length - OPENING_TAG.length,
      ]);
    }
  }
  return indices;
};

const GPTSearchResults = () => {
  const search = useSearchParams();

  const [, dispatch] = React.useContext(AppStateContext);
  const [stage, setStage] = React.useState<JSONAPI.GPTSearchStage>("filters");

  const query = search.get("q") ?? "";

  // When the user's query changes, reset the stage to "filters".
  React.useEffect(() => {
    setStage("filters");
  }, [query]);

  // Step 1: Extract filters from the user's query and initialize the search thread in the backend
  const {
    data: filterResp,
    error: filterError,
    isLoading: filtersAreLoading,
  } = useQuery({
    queryFn: () => gptSearch(query),
    queryKey: ["gpt-search", { query }],
    retry: 3,
  });

  const filters = filterResp?.lucene_filters;
  const requestId = filterResp?.request_id;

  // Step 2: Wait until the k-NN search has completed and return the results
  const {
    data: knnResp,
    error: knnError,
    isLoading: knnIsLoading,
  } = useQuery({
    enabled: stage === "knn",
    queryFn: () => gptSearchKnnResults(`${requestId}`),
    queryKey: ["gpt-search-knn-results", { requestId }],
    retry: 3,
  });

  const allDocs = knnResp?.docs;
  const numResults = allDocs?.length ?? 0;

  // Step 3: Wait until the GPT chat completions request has completed and return the answer
  const {
    data: answerResp,
    error: answerError,
    isLoading: answerIsLoading,
  } = useQuery({
    enabled: stage === "answer",
    queryFn: () => gptSearchAnswer(`${requestId}`),
    queryKey: ["gpt-search-answer", { requestId }],
    retry: 3,
  });

  const answer = answerResp?.answer;
  const supportingDocs = answerResp?.supporting_docs;
  const supportingDocsAsTickets = supportingDocs?.map(d => d.doc);

  React.useEffect(() => {
    if (answerResp) {
      dispatch?.({
        answer,
        numResults,
        timestamp: window.performance.now(),
        type: "SEARCH_END",
      });
    }
  }, [answer, answerResp, dispatch, numResults]);

  // TODO (renspoesse): pass on pagination functions once implemented.
  // TODO (renspoesse): implement these hooks and the TicketList component
  //  for the new sentiment search views.
  const [id, setId, { listId: listIdOfSelection }] = useTicketSelection([
    ...(supportingDocsAsTickets?.map(t => ({
      ...t,
      [LIST_ID_PROP]: "supporting",
    })) ?? []),
    ...(allDocs?.map(t => ({ ...t, [LIST_ID_PROP]: "top" })) ?? []),
  ]);
  useTicketAside(id);

  const { data: selected } = useTicketQuery(id);

  const highlight = React.useMemo(() => {
    const doc = supportingDocs?.find(
      d => selected && d.doc.jeeves_uid === selected.jeeves_uid,
    );
    return doc?.doc?.body_text
      ? getHighlightIndices(doc.bolded_body)
      : undefined;
  }, [supportingDocs, selected]);

  const handleClick = (t: JSONAPI.Ticket, listId: string) => {
    if (t.jeeves_uid === selected?.jeeves_uid && listId === listIdOfSelection) {
      dispatch?.({ type: "TOGGLE_ASIDE" });
    } else {
      setId(t.jeeves_uid, listId);
    }
  };

  // Scrolls the page to the top when fresh query data is loaded.
  React.useEffect(() => {
    if (filterResp || knnResp || answerResp) {
      window.scrollTo(0, 0);
    }
  }, [filterResp, knnResp, answerResp]);

  // Set the stage to "knn" once the filter extraction has completed.
  React.useEffect(() => {
    if (filterResp && !filterError && !filtersAreLoading) {
      setStage("knn");
    }
  }, [filterError, filtersAreLoading, filterResp]);

  // Set the stage to "answer" once the k-NN search has completed.
  React.useEffect(() => {
    if (knnResp && !knnError && !knnIsLoading) {
      setStage("answer");
    }
  }, [knnError, knnIsLoading, knnResp]);

  // Set the stage back to "filters" if any of the requests failed.
  React.useEffect(() => {
    if (
      (filterError && !filtersAreLoading) ||
      (knnError && !knnIsLoading) ||
      (answerError && !answerIsLoading)
    ) {
      setStage("filters");
    }
  }, [
    answerError,
    answerIsLoading,
    filterError,
    filtersAreLoading,
    knnError,
    knnIsLoading,
  ]);

  const renderAnswerResponse = (allKnnDocs: JSONAPI.Ticket[]) => (
    <>
      {answerIsLoading ? (
        <span>
          The search returned {numResults} results. Asking GPT to answer your
          query...
        </span>
      ) : answerResp?.error ? (
        <span className={styles.error}>{answerResp.error}</span>
      ) : answerResp && answer ? (
        <>
          <span className={styles.answer}>{answer}</span>
          {supportingDocsAsTickets?.length
            ? renderSupportingDocs(supportingDocsAsTickets)
            : null}
        </>
      ) : (
        <span className={styles.error}>
          The Jeeves API returned an error while retrieving the answer.
        </span>
      )}
      {renderDocs(allKnnDocs, "Top matches")}
      {renderAside()}
    </>
  );

  const renderAside = () =>
    selected
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
      : null;

  const renderDocs = (docs: JSONAPI.Ticket[], name: string) => (
    <NamedSection className={styles.section} name={name}>
      <TicketList
        bordered={false}
        onClick={ticket => handleClick(ticket, "top")}
        selectedId={listIdOfSelection === "top" ? id : undefined}
        tickets={docs}
      />
    </NamedSection>
  );

  const renderFilterTable = (
    luceneFilters: Record<string, string> | undefined,
  ) =>
    luceneFilters && Object.keys(luceneFilters).length ? (
      <Table>
        <thead>
          <tr>
            <th>Filter</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(luceneFilters).map((filter, i) => (
            <tr key={i}>
              <td>{filter[0]}</td>
              <td>{filter[1]}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    ) : null;

  const renderKnnResponse = () =>
    knnIsLoading ? (
      filters && Object.keys(filters).length ? (
        <>
          <span>Searching with the following filters:</span>
          {renderFilterTable(filters)}
        </>
      ) : (
        <span>Searching (this may take a while)...</span>
      )
    ) : knnResp?.error ? (
      <>
        <span className={styles.error}>
          {ERROR_MESSAGES[knnResp.error] ?? knnResp.error}
        </span>
        {renderFilterTable(filters)}
      </>
    ) : knnResp && allDocs?.length ? (
      renderAnswerResponse(allDocs)
    ) : (
      <>
        <span className={styles.error}>
          Jeeves returned an error while retrieving the search results.
        </span>
        {renderFilterTable(filters)}
      </>
    );

  const renderSupportingDocs = (docs: JSONAPI.Ticket[]) => (
    <NamedSection
      className={styles.section}
      name={`Top ${docs.length} supporting matches according to GPT`}
    >
      <TicketList
        bordered={false}
        onClick={ticket => handleClick(ticket, "supporting")}
        selectedId={listIdOfSelection === "supporting" ? id : undefined}
        tickets={docs}
      />
    </NamedSection>
  );

  return filtersAreLoading ? (
    <span>Extracting filters from your request...</span>
  ) : filterResp?.error ? (
    <span className={styles.error}>{filterResp.error}</span>
  ) : filterResp ? (
    renderKnnResponse()
  ) : (
    <span className={styles.error}>
      Jeeves returned an error while extracting filters for the search.
    </span>
  );
};

export default GPTSearchResults;
