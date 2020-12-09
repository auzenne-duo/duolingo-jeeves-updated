import * as React from "react";

import Table from "components/Table";
import Tag from "components/Tag";
import renderTicketSource from "components/renderTicketSource";
import styles from "styles/TicketTable.scss";
import {
  escapeHTML,
  formatReadableDate,
  highlightWord,
  normalizeNewLines,
} from "util";

interface Props {
  highlight?: string;
  ticket: JSONAPI.Ticket;
}

const TicketTable: React.FC<Props> = ({ highlight, ticket }) => {
  let body = normalizeNewLines(escapeHTML(ticket.body_text ?? ""))
    .trim()
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

  return (
    <Table className={styles.table}>
      <tbody>
        <tr>
          <th>Subject</th>
          <td>{ticket.header_text}</td>
        </tr>
        <tr>
          <th>Date</th>
          <td>
            {ticket.date_time
              ? formatReadableDate(new Date(ticket.date_time))
              : null}
          </td>
        </tr>
        <tr>
          <th>Source</th>
          <td>{renderTicketSource(ticket, { showUser: true })}</td>
        </tr>
        {ticket.priority || ticket.tags?.length ? (
          <tr>
            <th>Tags</th>
            <td>
              <div className={styles.tags}>
                {ticket.priority ? (
                  <Tag
                    className={styles.tag}
                    isPriority={["high", "urgent"].includes(ticket.priority)}
                    value={`${ticket.priority} priority`}
                  />
                ) : null}
                {ticket.tags?.map(tag => (
                  <Tag className={styles.tag} key={tag} value={tag} />
                ))}
              </div>
            </td>
          </tr>
        ) : null}
        <tr>
          <td
            colSpan={2}
            dangerouslySetInnerHTML={{
              __html: body,
            }}
          />
        </tr>
      </tbody>
    </Table>
  );
};

export default TicketTable;
