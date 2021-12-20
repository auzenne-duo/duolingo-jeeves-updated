import * as React from "react";

const getZendeskUser = (ticket: JSONAPI.Ticket) =>
  [
    ticket.via?.source?.from?.name,
    ticket.via?.source?.from?.address
      ? `<${ticket.via?.source?.from?.address}>`
      : undefined,
  ]
    .filter(part => part)
    .join(" ");

const renderTicketSource = (
  ticket: JSONAPI.Ticket,
  { showUser }: { showUser?: boolean } = { showUser: false },
) => {
  if (ticket.data_source === "AppFigures") {
    return (
      <>
        {showUser && ticket.author ? `${ticket.author} via ` : null}
        AppFigures, {ticket.store}
      </>
    );
  }

  if (ticket.data_source === "JIRA") {
    return (
      <>
        {showUser && ticket.username ? (
          <>
            <a
              href={`https://www.duolingo.com/diagnostics/user/summary/${encodeURIComponent(
                ticket.username,
              )}`}
            >
              {ticket.username}
            </a>
            {" via "}
          </>
        ) : null}
        <a
          href={`https://duolingo.atlassian.net/browse/${encodeURIComponent(
            ticket.issue_key as string,
          )}`}
        >
          {ticket.issue_key}
        </a>
      </>
    );
  }

  if (ticket.data_source === "Zendesk") {
    const zendeskUser = getZendeskUser(ticket);
    return (
      <>
        {showUser && zendeskUser ? (
          <>
            <a href={ticket.links?.[1]}>{zendeskUser}</a>
            {" via "}
          </>
        ) : null}
        <a href={ticket.links?.[0]}>
          Zendesk
          {ticket.via?.channel ? `, ${ticket.via?.channel}` : null}
        </a>
      </>
    );
  }

  return ticket.data_source;
};

export default renderTicketSource;
