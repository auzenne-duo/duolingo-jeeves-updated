import * as React from "react";

const renderTicketSource = (
  ticket: JSONAPI.Ticket,
  { showUser }: { showUser?: boolean } = { showUser: false },
) => {
  const user = [
    ticket.via?.source?.from?.name,
    ticket.via?.source?.from?.address
      ? `<${ticket.via?.source?.from?.address}>`
      : undefined,
  ]
    .filter(part => part)
    .join(" ");

  return ticket.data_source === "AppFigures" ? (
    `AppFigures, ${ticket.store}`
  ) : ticket.data_source === "JIRA" ? (
    <a
      href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
        ticket.issue_key as string,
      )}`}
    >
      {ticket.issue_key}
    </a>
  ) : ticket.data_source === "Zendesk" ? (
    <>
      {showUser && user ? (
        <>
          <a href={ticket.links?.[1]}>{user}</a>
          {` via `}
        </>
      ) : null}
      <a href={ticket.links?.[0]}>
        Zendesk
        {ticket.via?.channel ? `, ${ticket.via?.channel}` : null}
      </a>
    </>
  ) : (
    ticket.data_source
  );
};

export default renderTicketSource;
