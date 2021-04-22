import * as React from "react";
import { Link, useParams } from "react-router-dom";

import Table from "components/Table";
import TagFilter from "components/TagFilter";
import renderTicketSource from "components/renderTicketSource";
import imageCaretRight from "images/caret-right.svg";
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
  const { lang } = useParams<{ lang: JSONAPI.LanguageId }>();

  let body = normalizeNewLines(escapeHTML(ticket.body_text ?? ""))
    .trim()
    .replace(/\n/g, "<br />");
  body = highlight ? highlightWord(body, highlight) : body;

  return (
    <Table className={styles.table}>
      <tbody>
        <tr>
          <th>Subject</th>
          <td>
            <span className={styles.subject}>
              {ticket.header_text}
              <Link
                className={styles["icon-link"]}
                to={`/${lang}/discovery?id=${encodeURIComponent(
                  ticket.jeeves_uid,
                )}`}
              >
                <img
                  className={styles.icon}
                  alt="Open in Issue Discovery"
                  src={imageCaretRight}
                  title="Open in Issue Discovery"
                />
              </Link>
            </span>
          </td>
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
                  <TagFilter
                    className={styles.tag}
                    field="priority"
                    isPriority={["high", "highest", "urgent"].includes(
                      ticket.priority.toLowerCase(),
                    )}
                    text={`${ticket.priority} priority`}
                    value={ticket.priority}
                  />
                ) : null}
                {ticket.tags?.map(tag => (
                  <TagFilter
                    className={styles.tag}
                    field="tags"
                    key={tag}
                    value={tag}
                  />
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
